import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Industry Insight v3.3", layout="wide")

# 🌟 Gemini API 설정 (가장 안정적인 경로 고정)
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

# 카테고리 설정
NAVER_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "캐주얼", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "지갑/벨트", "시계/쥬얼리", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "모바일/PC"],
    "식품": ["농/수/축산물", "가공식품", "음료", "과자/베이커리", "건강식품"],
    "스포츠/레저": ["골프", "캠핑/낚시", "등산", "피트니스"],
    "가구/인테리어": ["침실/거실가구", "주방가구", "인테리어소품", "침구/커튼"],
    "생활/건강": ["주방용품", "세탁용품", "반려동물", "의료기기"]
}

# 세션 상태 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3.5em; }
    .ai-report-card { padding: 25px; background-color: #F8F9FA; border-radius: 15px; border-left: 10px solid #FFB300; margin-bottom: 20px; line-height: 1.8; color: #333; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🚀 AE Insight Pro v3.3")
    main_menu = st.radio("메뉴 선택", ["업종별 트렌드 분석", "가망 광고주 제안 솔루션", "광고주 DB 관리", "소통 키워드 분석"])

# 고품질 키워드 추출 함수
def extract_hq_keywords(titles, industry):
    if not ai_engine: return " ".join(titles)
    try:
        prompt = f"광고 AE 관점에서 {industry} 업계 뉴스 {titles}를 분석해 소비자 결핍이나 트렌드가 담긴 전략 키워드 15개를 콤마로 구분해줘."
        response = ai_engine.generate_content(prompt)
        return response.text.replace(',', ' ')
    except: return " ".join(titles)

def create_styled_wc(text, font_path):
    wc = WordCloud(font_path=font_path, width=1200, height=700, background_color='white', colormap='tab10', max_words=50).generate(text)
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- [기능 1: 업종별 트렌드 분석] ---
if main_menu == "업종별 트렌드 분석":
    st.header("📈 업종별 전략 트렌드 분석")
    c1, c2 = st.columns(2)
    with c1: m_cat = st.selectbox("대분류", list(NAVER_CATEGORIES.keys()))
    with c2: s_cat = st.selectbox("중분류", NAVER_CATEGORIES[m_cat])
    
    period = st.select_slider("분석 기간 설정", options=["3일", "7일", "한달", "60일", "분기"], value="60일")
    
    if st.button(f"🚀 {s_cat} 전략 분석"):
        with st.spinner("데이터 분석 중..."):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss); titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:20]]
            
            if titles:
                hq_words = extract_hq_keywords(titles, s_cat)
                if ai_engine:
                    resp = ai_engine.generate_content(f"AE 관점에서 {s_cat} {period} 트렌드 제안 포인트를 써줘: {titles}")
                    st.markdown(f'<div class="ai-report-card"><b>🤖 AI 전략 제안</b><br><br>{resp.text}</div>', unsafe_allow_html=True)
                st.pyplot(create_styled_wc(hq_words, FONT_PATH))

# --- [기능 3: 광고주 DB 관리 (개선)] ---
elif main_menu == "광고주 DB 관리":
    st.header("📂 광고주 소통 데이터 관리")
    
    with st.expander("➕ 새 소통 내용 기록하기", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            new_date = st.date_input("날짜", datetime.date.today())
            new_client = st.text_input("광고주명")
        with col2:
            new_content = st.text_area("소통 내용 (업무 이슈, 피드백 등)")
        
        if st.button("💾 데이터 저장하기"):
            if new_client and new_content:
                new_data = pd.DataFrame({'날짜': [pd.to_datetime(new_date)], '광고주명': [new_client], '소통내용': [new_content]})
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_data], ignore_index=True)
                st.success(f"{new_client} 소통 내용이 저장되었습니다!")
            else:
                st.error("광고주명과 내용을 모두 입력해주세요.")

    st.divider()
    st.subheader("🔍 저장된 데이터 확인")
    up_f = st.file_uploader("💾 기존 XLSX 파일 업로드", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        st.session_state.history_db = df
    
    search = st.text_input("광고주 검색")
    display_df = st.session_state.history_db.copy()
    if search:
        display_df = display_df[display_df['광고주명'].str.contains(search, na=False)]
    st.dataframe(display_df, use_container_width=True)

# --- [기능 4: 소통 키워드 분석] ---
elif main_menu == "소통 키워드 분석":
    st.header("📊 광고주별 핵심 이슈 분석")
    if st.session_state.history_db.empty:
        st.info("광고주 DB 관리 메뉴에서 먼저 데이터를 입력해주세요.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            target = st.selectbox("분석할 광고주", sorted(st.session_state.history_db['광고주명'].unique()))
        with c2:
            st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'])
            min_d = st.session_state.history_db['날짜'].min().date()
            date_range = st.date_input("분석 기간 설정", [min_d, datetime.date.today()])

        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]

        if not f_df.empty:
            all_text = " ".join(f_df['소통내용'].astype(str))
            refined = extract_hq_keywords([all_text], f"{target} 소통")
            fig = create_styled_wc(refined, FONT_PATH)
            st.pyplot(fig)
            buf = BytesIO(); fig.savefig(buf, format="png")
            st.download_button("📥 분석 이미지 저장", buf.getvalue(), f"{target}_분석.png")

# --- [기능 2: 가망 광고주 제안] ---
elif main_menu == "가망 광고주 제안 솔루션":
    st.header("🎯 가망 광고주 제안서 자동 생성")
    t_url = st.text_input("광고주 URL")
    if st.button("💡 제안서 생성"):
        if ai_engine:
            resp = ai_engine.generate_content(f"{t_url} 광고주를 위한 마케팅 제안서를 AE 말투로 써줘.")
            st.markdown(f'<div class="ai-report-card">{resp.text}</div>', unsafe_allow_html=True)
