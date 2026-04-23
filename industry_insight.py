import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.7", layout="wide")

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
    .issue-tag { display: inline-block; padding: 10px 22px; margin: 5px; background-color: #FFF9E6; border: 2px solid #FFB300; border-radius: 50px; font-weight: bold; color: #E65100; font-size: 0.95em; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 🌟 [v13.7 핵심] 제안서용 고품질 키워드 정제 함수
def get_premium_keywords(titles, context):
    if not ai_engine or not titles: return ["#데이터분석중"]
    
    prompt = f"""
    당신은 광고 대행사의 전략 기획 본부장입니다. 다음 {context} 데이터를 분석해 광고주 제안서의 '핵심 인사이트' 섹션에 바로 넣을 수 있는 단어를 선별하세요.
    
    [가이드라인]
    1. '~하는', '~까지', '~보다' 같은 조사나 불완전한 단어는 절대 금지.
    2. 소비자의 결핍(Pain-point), 타겟 라이프스타일, 핵심 성분/효능 위주로 추출.
    3. 명사형으로 딱 떨어지게 5개만 추출. (예: #관절연골, #액티브시니어, #무릎보호, #조기치료, #프리미엄영양제)
    
    데이터: {titles}
    """
    try:
        resp = ai_engine.generate_content(prompt)
        keywords = re.findall(r'#\w+', resp.text)
        return [k for k in keywords if len(k) > 2][:5]
    except:
        return ["#인사이트도출"]

# 🌟 워드클라우드 클리닝 로직 (불필요 단어 제거)
def create_cleaned_wc(text_list, height=600):
    full_text = " ".join(text_list)
    # AE 업무에 불필요한 단어 필터링
    stop_words = ["뉴스", "제목", "기자", "오늘", "제공", "사진", "출처", "통해", "대한", "관련", "위해", "지난", "이번"]
    
    wc = WordCloud(
        font_path=FONT_PATH, width=1200, height=height,
        background_color='white', colormap='tab10',
        stopwords=set(stop_words),
        max_words=60, min_font_size=10,
        regexp=r"\w{2,}" # 2글자 이상의 단어만 추출
    ).generate(full_text)
    
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 및 메인 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.7")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar 로직
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 관절 영양제", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="n_p")
        
        if st.button("🚀 전략 뉴스 분석 시작"):
            with st.spinner("AI 본부장이 데이터를 정제 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                    if titles:
                        tags = get_premium_keywords(titles, "뉴스")
                        st.markdown("<div class='section-header'>💡 제안서용 핵심 소구점 (Key Selling Points)</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                        st.pyplot(create_cleaned_wc(titles))
                    else: st.warning("데이터 수집 실패")
                except: st.error("통신 장애")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="s_p")
        if st.button("🔍 시장 니즈 분석 시작"):
            with st.spinner("소비자 보이스 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
                titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
                if titles:
                    tags = get_premium_keywords(titles, "시장검색")
                    st.markdown("<div class='section-header'>🎯 마케팅 타겟 인사이트</div>", unsafe_allow_html=True)
                    st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                    st.pyplot(create_cleaned_wc(titles))

# 이후 관리 메뉴들 유지 (v13.6과 동일)
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    st.dataframe(st.session_state.history_db)
