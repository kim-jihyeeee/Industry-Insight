import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.0", layout="wide", initial_sidebar_state="auto")

# 🌟 Gemini API 설정 (에러 방지 경로 고정)
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

# 세션 상태 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용'])

# UI 스타일
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 25px; margin: 5px; background-color: #ffffff; border: 1px solid #ddd; border-radius: 5px; font-weight: bold; color: #555; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .section-header { font-size: 1.3em; font-weight: bold; margin: 25px 0 15px 0; color: #333; border-bottom: 2px solid #FFB300; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.0")
    st.markdown("### 📂 내부 히스토리 관리")
    main_menu = st.radio("메뉴 선택", ["광고주 DB 관리", "관리 이력 입력", "디지털 리포트(내부)"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### 📊 외부 시장 분석")
    market_radar = st.checkbox("🌐 AI Trend Radar", value=True)

# 시각화 함수
def create_wc(text):
    if not text.strip(): return None
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=600, background_color='white', colormap='tab10', max_words=50).generate(text)
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- [메인 화면 로직] ---

# 1. AI Trend Radar (외부 시장 분석)
if market_radar:
    st.title("🌐 AI Trend Radar v13.0")
    tab1, tab2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])

    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1: n_keyword = st.text_input("뉴스 분석 키워드", placeholder="도라지배즙", key="n_k")
        with c2: n_period = st.selectbox("수집 기간", ["3일", "7일", "30일", "60일"], key="n_p")
        
        if st.button("🚀 뉴스 AI 분석 시작"):
            with st.spinner("AI가 최신 뉴스를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=10)
                    soup = BeautifulSoup(res.text, 'xml')
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in soup.find_all('item')[:20]]
                    
                    if titles:
                        prompt = f"이 뉴스 제목들에서 AE 제안용 핵심 키워드 5개만 #단어 형태로 뽑아줘: {titles}"
                        tags_text = ai_engine.generate_content(prompt).text
                        tags = re.findall(r'#\w+', tags_text)
                        
                        st.markdown("<div class='section-header'>📌 실시간 주요 이슈 키워드</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{tag}</span>" for tag in tags[:5]]), unsafe_allow_html=True)
                        
                        st.markdown("<div class='section-header'>☁️ 뉴스 트렌드 워드클라우드</div>", unsafe_allow_html=True)
                        fig = create_wc(" ".join(titles))
                        if fig: st.pyplot(fig)
                    else: st.warning("데이터 수집에 실패했습니다. 키워드를 확인해 주세요.")
                except: st.error("데이터 통신 중 오류가 발생했습니다.")

    with tab2:
        c1, c2 = st.columns([3, 1])
        with c1: s_keyword = st.text_input("검색 트렌드 키워드", placeholder="예: 봄 환절기 건강 관리", key="s_k")
        with c2: s_period = st.selectbox("수집 기간", ["3일", "7일", "30일", "60일"], index=1, key="s_p")
        
        if st.button("🔍 검색 AI 분석 시작"):
            with st.spinner("대중 검색 트렌드 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+비교&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:20]]
                    if titles:
                        prompt = f"이 검색 트렌드 데이터에서 소비자의 니즈가 담긴 키워드 5개를 #단어 형태로 뽑아줘: {titles}"
                        tags = re.findall(r'#\w+', ai_engine.generate_content(prompt).text)
                        st.markdown("<div class='section-header'>🎯 대중 관심사 해시태그</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{tag}</span>" for tag in tags[:5]]), unsafe_allow_html=True)
                        
                        fig = create_wc(" ".join(titles))
                        if fig: st.pyplot(fig)
                    else: st.warning("데이터가 부족합니다.")
                except: st.error("분석 중 오류가 발생했습니다.")

# 2. 내부 히스토리 관리 메뉴들
st.divider()

if main_menu == "광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일(XLSX) 업로드 및 복구", type=['xlsx'])
    if up_f:
        try:
            df = pd.read_excel(up_f, engine='openpyxl')
            st.session_state.history_db = df
            st.success("✅ 데이터 로드 완료!")
        except: st.error("파일 로드 실패")
    
    search_q = st.text_input("🔍 광고주 검색")
    display_df = st.session_state.history_db.copy()
    if search_q:
        display_df = display_df[display_df['광고주명'].str.contains(search_q, na=False, case=False)]
    st.dataframe(display_df, use_container_width=True)

elif main_menu == "관리 이력 입력":
    st.header("📝 관리 이력 직접 입력")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        in_date = col1.date_input("날짜", datetime.date.today())
        in_name = col2.text_input("광고주명")
        in_content = st.text_area("소통 내용 (피드백, 요청사항 등)")
        if st.form_submit_button("💾 데이터 저장"):
            if in_name and in_content:
                new_row = pd.DataFrame({'날짜': [str(in_date)], '광고주명': [in_name], '소통내용': [in_content]})
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success(f"✅ {in_name} 데이터 저장 완료!")
            else: st.error("필수 항목을 입력하세요.")

elif main_menu == "디지털 리포트(내부)":
    st.header("📊 내부 소통 이슈 리포트")
    if not st.session_state.history_db.empty:
        client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique())
        target = st.selectbox("분석할 광고주 선택", client_list)
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        
        if not f_df.empty:
            text_data = " ".join(f_df['소통내용'].fillna('').astype(str))
            st.markdown(f"### 🎯 {target} 주요 소통 이슈")
            fig = create_wc(text_data)
            if fig: st.pyplot(fig)
        else: st.warning("분석할 데이터가 없습니다.")
    else: st.info("DB에 데이터가 없습니다. 먼저 이력을 입력하거나 파일을 업로드하세요.")
