import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v3.0", layout="wide")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('models/gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
        res = requests.get(url)
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

FONT_PATH = load_font()

# 카테고리 구성
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC", "영상/음향가전"],
    "식품": ["농/수/축산물", "반찬/가공식품", "음료", "과자/베이커리", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "헬스/요가", "수영/스포츠의류"],
    "가구/인테리어": ["침실/거실가구", "주방가구", "인테리어소품", "침구/커튼"],
    "생활/건강": ["주방/욕실용품", "세탁/생활용품", "반려동물", "의료기기/건강용품"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '핵심키워드'])

# UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 15px; border-left: 10px solid #FFB300; margin-bottom: 20px; line-height: 1.8; color: #333; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 Industry Insight v3.0")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 🌟 [개선] 뉴스+검색 트렌드 통합 키워드 추출 함수
def extract_trend_keywords(titles, industry):
    if not ai_engine: return " ".join(titles)
    try:
        # 뉴스 제목뿐만 아니라 대중의 검색 의도(Search Intent)를 추론하도록 프롬프트 강화
        prompt = f"""
        당신은 데이터 분석 전문가이자 광고 AE입니다. 
        아래 뉴스 제목들을 참고하여 {industry} 업계에서 대중들이 실제로 포털에 많이 검색했을 법한 '실제 검색 데이터 키워드'와 '핵심 전략 키워드' 20개를 추출해줘.
        단순한 단어 나열이 아니라, '발레코어룩', '가성비 선물' 처럼 실제 소비자의 의도가 담긴 유의미한 키워드 위주로 뽑아줘.
        결과는 콤마로만 구분해줘.
        데이터: {titles}
        """
        response = ai_engine.generate_content(prompt)
        return response.text.replace(',', ' ')
    except:
        return " ".join(titles)

def create_styled_wc(text, font_path):
    wc = WordCloud(
        font_path=font_path, width=1200, height=700,
        background_color='white', colormap='Set2',
        max_words=60, relative_scaling=0.5
    ).generate(text)
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업종 뉴스 & 실시간 검색 트렌드 리포트")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[m_cat])
    
    period_label = st.select_slider("분석 기간 설정", options=["3일", "7일", "한달", "60일", "분기"], value="60일")
    
    if st.button(f"🚀 {s_cat} 통합 트렌드 분석"):
        with st.spinner("뉴스 및 대중 검색 키워드를 매칭 중입니다..."):
            # 검색 데이터의 느낌을 주기 위해 쿼리를 다각화하여 수집
            queries = [f"{s_cat} 추천", f"{s_cat} 트렌드", f"{s_cat} 순위"]
            all_titles = []
            for q in queries:
                rss = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss); soup = BeautifulSoup(res.text, 'xml')
                all_titles.extend([re.split(r' - | \| ', i.title.get_text())[0] for i in soup.find_all('item')[:10]])
            
            if all_titles:
                # 🌟 뉴스 제목 + 대중 검색 의도를 반영한 AI 키워드 추출
                combined_keywords = extract_trend_keywords(all_titles, s_cat)
                
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} 업계의 실시간 뉴스 및 검색 데이터 특징을 분석하고 전략을 제안해줘: {all_titles}")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 AI 트렌드 & 검색 데이터 통합 분석</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: pass
                
                fig = create_styled_wc(combined_keywords, FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 통합 리포트 저장", buf.getvalue(), f"{s_cat}_통합분석.png", "image/png")

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 이슈 분석")
    if st.session_state.history_db.empty:
        st.info("광고주 DB 관리 메뉴에서 데이터를 먼저 업로드해주세요.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].dropna().unique()))
        with c2:
            st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'], errors='coerce')
            min_date = st.session_state.history_db['날짜'].min().date() if not st.session_state.history_db['날짜'].isnull().all() else datetime.date.today()
            max_date = datetime.date.today()
            date_range = st.date_input("분석 기간 설정", [min_date, max_date])

        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]

        if not f_df.empty:
            with st.spinner("소통 내역 분석 중..."):
                text = " ".join(f_df['소통내용'].fillna('').astype(str))
                refined_text = extract_trend_keywords([text], f"{target} 소통내역")
                fig = create_styled_wc(refined_text, FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button(f"📥 {target} 분석 저장", buf.getvalue(), f"{target}_분석.png", "image/png")

# --- 나머지 메뉴 (가망 광고주, DB관리) ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 맞춤 제안")
    t_url = st.text_input("가망 광고주 URL")
    if st.button("💡 제안서 생성"):
        brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
        resp = ai_engine.generate_content(f"광고주 {brand}를 위한 실시간 검색 트렌드 기반 제안서를 써줘.")
        st.markdown(f'<div class="ai-report-card">{resp.text}</div>', unsafe_allow_html=True)

elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리")
    up_f = st.file_uploader("💾 XLSX 업로드", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
        df.columns = [rename_map.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("로드 완료")
    st.dataframe(st.session_state.history_db, use_container_width=True)
