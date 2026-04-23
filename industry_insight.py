import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v2.9", layout="wide")

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

# 카테고리 구성 (네이버 데이터랩 기준)
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
    st.title("🚀 Industry Insight v2.9")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 🌟 [개선] AI 기반 전략 키워드 추출 함수
def extract_ai_keywords(text_list, context_info):
    if not ai_engine: return " ".join(text_list)
    try:
        prompt = f"다음은 {context_info} 관련 텍스트 데이터다. AE가 마케팅 전략 수립에 활용할 수 있는 핵심 키워드 15개만 추출해서 콤마로 구분해줘: {text_list}"
        response = ai_engine.generate_content(prompt)
        return response.text.replace(',', ' ')
    except:
        return " ".join(text_list)

def create_styled_wc(text, font_path):
    wc = WordCloud(
        font_path=font_path, width=1200, height=700,
        background_color='white', colormap='tab10',
        max_words=60, relative_scaling=0.5
    ).generate(text)
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업종별 트렌드 분석 리포트")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류 선택", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류 선택", NAVER_CATEGORIES[m_cat])
    
    period_label = st.select_slider("분석 기간 설정", options=["3일", "7일", "한달", "60일", "분기"], value="60일")
    
    if st.button(f"🚀 {s_cat} 전략 리포트 생성"):
        with st.spinner("AI가 최신 트렌드에서 인사이트를 추출 중입니다..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+업계+뉴스&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); soup = BeautifulSoup(res.text, 'xml')
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in soup.find_all('item')[:25]]
            
            if titles:
                # 🌟 AI가 뉴스 제목에서 전략적 키워드만 선별
                ai_keywords = extract_ai_keywords(titles, s_cat)
                
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} 업계 트렌드를 분석하고 캠페인 전략을 제안해줘: {titles}")
                        st.markdown(f'<div class="ai-report-card"><b>🤖 AI 전략 제안</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: pass
                
                fig = create_styled_wc(ai_keywords, FONT_PATH)
                st.pyplot(fig)
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button("📥 리포트 이미지 저장", buf.getvalue(), f"{s_cat}_분석.png", "image/png")

# --- [기능 2: 가망 광고주 제안 솔루션] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 맞춤 제안")
    t_url = st.text_input("분석할 가망 광고주 URL", placeholder="https://...")
    cc1, cc2 = st.columns(2)
    with cc1: pm_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()), key="pro_m")
    with cc2: ps_cat = st.selectbox("중분류", NAVER_CATEGORIES[pm_cat], key="pro_s")
    
    if st.button("💡 전략 제안서 생성"):
        if not t_url: st.warning("URL을 입력하세요.")
        else:
            with st.spinner("AI 분석 중..."):
                brand = re.sub(r'https?://|www\.|brand\.naver\.com/|\.com|\.co\.kr|/', '', t_url)
                if ai_engine:
                    try:
                        resp = ai_engine.generate_content(f"광고주 {brand}, 업종 {ps_cat} 제안서 작성해줘.")
                        st.markdown(f'<div class="ai-report-card"><b>💡 {brand} 제안 솔루션</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI 서버 연결 실패")

# --- [기능 3: DB 관리] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 데이터 통합 관리")
    up_f = st.file_uploader("💾 백업 데이터 업로드 (XLSX)", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        rename_map = {'업체명': '광고주명', '광고주': '광고주명', '내용': '소통내용'}
        df.columns = [rename_map.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("데이터 로드 완료!")
    st.divider()
    search = st.text_input("🔍 광고주 검색")
    d_df = st.session_state.history_db.copy()
    if search: d_df = d_df[d_df['광고주명'].str.contains(search, na=False, case=False)]
    st.dataframe(d_df, use_container_width=True)

# --- [기능 4: 소통 키워드 분석 (개선)] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주 소통 이슈 분석")
    if st.session_state.history_db.empty:
        st.info("광고주 DB 관리 메뉴에서 데이터를 먼저 업로드해주세요.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            target = st.selectbox("광고주 선택", sorted(st.session_state.history_db['광고주명'].dropna().unique()))
        with c2:
            # 🌟 기간 설정 기능 추가
            st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'], errors='coerce')
            min_date = st.session_state.history_db['날짜'].min().date() if not st.session_state.history_db['날짜'].isnull().all() else datetime.date.today()
            max_date = datetime.date.today()
            date_range = st.date_input("분석 기간 설정", [min_date, max_date])

        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]

        if not f_df.empty:
            with st.spinner("소통 내역에서 핵심 이슈를 추출 중입니다..."):
                text = " ".join(f_df['소통내용'].fillna('').astype(str))
                refined_text = extract_ai_keywords([text], f"{target} 소통내역")
                
                fig = create_styled_wc(refined_text, FONT_PATH)
                st.pyplot(fig)
                
                # 🌟 이미지 저장 기능 추가
                buf = BytesIO(); fig.savefig(buf, format="png")
                st.download_button(f"📥 {target} 분석 이미지 저장", buf.getvalue(), f"{target}_분석.png", "image/png")
        else:
            st.warning("선택한 기간에 소통 데이터가 없습니다.")
