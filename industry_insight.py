import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.8", layout="wide")

# 🌟 Gemini API 설정
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash-latest')
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

# 세션 데이터 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 22px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; font-size: 0.95em; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 🌟 [v13.8] 키워드 5개 강제 추출 로직
def get_refined_keywords(titles, context):
    if not ai_engine or not titles: return ["#데이터분석중"]
    
    prompt = f"""
    당신은 전문 마케팅 전략가입니다. 다음 {context} 데이터를 분석해 광고주 제안에 활용할 핵심 키워드 5개를 명사형으로 추출하세요.
    - 불필요한 조사, 형용사 금지
    - 반드시 #단어 #단어 #단어 #단어 #단어 형식으로 5개를 꽉 채워서 대답하세요.
    - 데이터와 가장 밀접한 구체적인 단어를 선택하세요.
    
    데이터: {titles}
    """
    try:
        resp = ai_engine.generate_content(prompt)
        # #으로 시작하는 단어들 모두 찾기
        keywords = re.findall(r'#\w+', resp.text)
        # 5개 미만일 경우 제목에서 단어를 직접 추출해서라도 채움
        if len(keywords) < 5:
            backup_words = [f"#{w}" for w in " ".join(titles).split() if len(w) > 1]
            keywords = (keywords + backup_words)[:5]
        return keywords[:5]
    except:
        return ["#인사이트", "#트렌드", "#시장분석", "#이슈추적", "#전략수립"]

def create_cleaned_wc(text_list, height=600):
    full_text = " ".join(text_list)
    stop_words = ["뉴스", "제목", "기자", "제공", "사진", "대한", "관련", "위해", "지난", "이번", "경우", "함께"]
    
    wc = WordCloud(
        font_path=FONT_PATH, width=1200, height=height,
        background_color='white', colormap='tab10',
        stopwords=set(stop_words),
        max_words=60, min_font_size=10,
        regexp=r"\w{2,}"
    ).generate(full_text)
    
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 및 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.8")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 관절 영양제", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="n_p")
        
        if st.button("🚀 전략 뉴스 분석 시작"):
            with st.spinner("최신 뉴스 데이터를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                    if titles:
                        tags = get_refined_keywords(titles, "뉴스")
                        st.markdown("<div class='section-header'>📌 제안용 핵심 소구점 (Key Selling Points)</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                        st.pyplot(create_cleaned_wc(titles))
                    else: st.warning("데이터 수집 실패")
                except: st.error("통신 장애")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="s_p")
        if st.button("🔍 시장 니즈 분석 시작"):
            with st.spinner("대중 검색 트렌드를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
                titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
                if titles:
                    tags = get_refined_keywords(titles, "시장검색")
                    st.markdown("<div class='section-header'>🎯 마케팅 타겟 인사이트</div>", unsafe_allow_html=True)
                    st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                    st.pyplot(create_cleaned_wc(titles))

# 이후 관리 메뉴들 동일하게 유지
