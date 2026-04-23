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

# 세션 상태 초기화 (기존 데이터 유지용)
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용'])

# UI 스타일 설정
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: visible; } 
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 25px; margin: 5px; background-color: #ffffff; border: 1px solid #ddd; border-radius: 5px; font-weight: bold; color: #555; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .section-header { font-size: 1.3em; font-weight: bold; margin: 25px 0 15px 0; color: #333; }
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

# 워드클라우드 생성 함수
def create_wc(text):
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=600, background_color='white', colormap='tab10', max_words=50).generate(text)
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- [메인 화면: AI Trend Radar] ---
if market_radar:
    st.title("🌐 AI Trend Radar v13.0")
    
    # 레퍼런스 스타일의 탭 구성
    tab1, tab2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])

    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1: n_keyword = st.text_input("뉴스 분석 키워드", placeholder="도라지배즙", key="n_k")
        with c2: n_period = st.selectbox("수집 기간", ["3일", "7일", "30일", "60일"], key="n_p")
        
        if st.button("🚀 뉴스 AI 분석 시작"):
            with st.spinner("AI가 최신 뉴스를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss); soup = BeautifulSoup(res.text, 'xml')
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in soup.find_all('item')[:20]]
                
                if titles:
                    # 1. AI 핵심 키워드 필터링 (상위 5개)
                    prompt = f"이 뉴스 제목들에서 AE가 주목해야 할 핵심 키워드 5개만 #단어 형태로 뽑아줘: {titles}"
                    tags_text = ai_engine.generate_content(prompt).text
                    tags = re.findall(r'#\w+', tags_text)
                    
                    st.markdown("<div class='section-header'>📌 실시간 주요 이슈 키워드</div>", unsafe_allow_html=True)
                    tag_html = "".join([f"<span class='issue-tag'>{tag}</span>" for tag in tags[:5]])
                    st.markdown(tag_html, unsafe_allow_html=True)
                    
                    # 2. 워드클라우드
                    st.markdown("<div class='section-header'>☁️ 뉴스 트렌드 워드클라우드</div>", unsafe_allow_html=True)
                    st.pyplot(create_wc(" ".join(titles)))
                    
                    # 3. 뉴스 리스트 테이블 형태
                    with st.expander("📂 수집 데이터 원문 확인"):
                        st.table(pd.DataFrame({"뉴스 제목": titles}))
                else: st.warning("데이터가 없습니다.")

    with tab2:
        c1, c2 = st.columns([3, 1])
        with c1: s_keyword = st.text_input("검색 트렌드 키워드", placeholder="예: 봄 환절기 선물", key="s_k")
        with c2: s_period = st.selectbox("수집 기간", ["3일", "7일", "30일", "60일"], key="s_p")
        
        if st.button("🔍 검색 AI 분석 시작"):
            with st.spinner("대중 검색 데이터를 분석 중입니다..."):
                # 검색 데이터 느낌을 위해 '추천', '비교' 쿼리 조합
                rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+비교&hl=ko&gl=KR&ceid=KR:ko"
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:20]]
                
                if titles:
                    prompt = f"이 검색 결과에서 대중의 실제 구매 의도가 담긴 핵심 키워드 5개를 #단어 형태로 뽑아줘: {titles}"
                    tags_text = ai_engine.generate_content(prompt).text
                    tags = re.findall(r'#\w+', tags_text)
                    
                    st.markdown("<div class='section-header'>🎯 대중 관심사 해시태그</div>", unsafe_allow_html=True)
                    tag_html = "".join([f"<span class='issue-tag'>{tag}</span>" for tag in tags[:5]])
                    st.markdown(tag_html, unsafe_allow_html=True)
                    
                    st.pyplot(create_wc(" ".join(titles)))
                else: st.warning("데이터가 부족합니다.")

# --- 내부 관리 메뉴 유지 ---
if main_menu == "광고주 DB 관리":
    st.title("📂 광고주 DB 관리")
    st.dataframe(st.session_state.history_db, use_container_width=True)
