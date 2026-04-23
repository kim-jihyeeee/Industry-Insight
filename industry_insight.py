import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v14.1", layout="wide")

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

# 🌟 [v14.1 핵심] AI 실패 시 데이터 기반 강제 추출 로직 (이중 방어)
def get_failsafe_keywords(titles):
    if not titles: return ["#데이터수집오류"]
    
    # 1단계: AI에게 전략 키워드 요청
    prompt = f"다음 뉴스 제목들에서 AE 제안서용 핵심 명사 5개만 #단어 형태로 뽑아줘. (이슈, 트렌드, 분석 같은 뻔한 단어 절대 금지): {titles}"
    try:
        resp = ai_engine.generate_content(prompt)
        keywords = re.findall(r'#\w+', resp.text)
        # 뻔한 단어가 섞여있는지 검사 (지혜님 요청 반영)
        forbidden = ['이슈', '트렌드', '분석', '시장', '전략', '수립', '인사이트']
        filtered = [k for k in keywords if not any(f in k for f in forbidden)]
        if len(filtered) >= 5: return filtered[:5]
    except: pass

    # 2단계: AI 실패 시 직접 텍스트 분석 (빈도수 상위 명사 강제 추출)
    combined_text = " ".join(titles)
    words = re.findall(r'[가-힣]{2,}', combined_text)
    stop_words = ['뉴스', '제목', '기자', '지난', '이번', '통해', '함께', '오전', '오후', '대한', '관련']
    filtered_words = [w for w in words if w not in stop_words]
    
    counts = Counter(filtered_words)
    top_5 = [f"#{w}" for w, c in counts.most_common(5)]
    
    return top_5 if len(top_5) >= 5 else ["#분석데이터부족"]

# 🌟 [오류 수정 완료] 워드클라우드 생성 함수
def create_cleaned_wc(text_list, height=600):
    full_text = " ".join(text_list)
    stop_words = ["뉴스", "제목", "기자", "제공", "사진", "대한", "관련", "위해", "지난", "이번", "경우", "함께", "있다", "했다", "오전", "오후"]
    
    wc = WordCloud(
        font_path=FONT_PATH, width=1200, height=height,
        background_color='white', colormap='tab10',
        stopwords=set(stop_words),
        max_words=60, min_font_size=10,
        regexp=r"[가-힣]{2,}"
    ).generate(full_text)
    
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 및 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v14.1")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 무릎 연골", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="n_p")
        
        if st.button("🚀 전략 뉴스 분석 시작"):
            with st.spinner("최신 데이터를 정밀 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                    if titles:
                        tags = get_failsafe_keywords(titles)
                        st.markdown("<div class='section-header'>📌 시장 실시간 핵심 키워드</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                        st.pyplot(create_cleaned_wc(titles))
                    else: st.warning("데이터가 없습니다.")
                except: st.error("통신 오류가 발생했습니다.")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="s_p")
        if st.button("🔍 시장 니즈 분석 시작"):
            with st.spinner("소비자 관심사를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
                titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
                if titles:
                    tags = get_failsafe_keywords(titles)
                    st.markdown("<div class='section-header'>🎯 대중 관심사 실시간 태그</div>", unsafe_allow_html=True)
                    st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                    st.pyplot(create_cleaned_wc(titles))

# 이후 DB 관리 및 리포트 기능 유지 (중복 생략)
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("파일 업로드", type=['xlsx'])
    if up_f:
        st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
    st.dataframe(st.session_state.history_db)

elif main_menu == "📝 관리 이력 입력":
    st.header("📝
