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
st.set_page_config(page_title="AE Total Tool v14.7", layout="wide")

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

# 세분화 카테고리
DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "언더웨어"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전"],
    "식품": ["건강식품", "다이어트식품", "음료", "신선식품", "가공식품"],
    "스포츠/레저": ["골프", "캠핑", "피트니스"],
    "생활/건강": ["주방용품", "욕실용품", "반려동물", "의료기기"]
}

# 세션 초기화 및 DB 열 이름 표준화 함수
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_db(df):
    # 🌟 어떤 이름이든 표준 이름으로 매칭 (KeyError 방지)
    rename_map = {
        '날짜': ['날짜', '일자', '등록일', 'Date'],
        '광고주명': ['광고주명', '광고주', '업체명', 'Client'],
        '소통내용': ['소통내용', '내용', '상담내용', '상세내용', '소통'],
        '대분류': ['대분류', '카테고리', '업종'],
        '소분류': ['소분류', '세부카테고리', '세부업종']
    }
    new_cols = {}
    for standard, variations in rename_map.items():
        for col in df.columns:
            if col in variations:
                new_cols[col] = standard
    return df.rename(columns=new_cols)

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 22px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 🌟 [v14.7] 워드클라우드 무의미 키워드 제거 강화
def create_cleaned_wc(text_data, height=600):
    if isinstance(text_data, pd.Series): text_list = text_data.dropna().astype(str).tolist()
    else: text_list = text_data
    full_text = " ".join(text_list)
    if not full_text.strip(): return None, None

    # 마케팅에 불필요한 단어들 싹 제거
    stop_words = ["뉴스", "제목", "기자", "지난", "이번", "통해", "함께", "대한", "관련", "위해", "있는", "합니다", "했다", "입니다", "경우", "제공", "사진", "오전", "오후", "오늘", "내일"]
    
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', 
                   stopwords=set(stop_words), regexp=r"[가-힣]{2,}", max_words=80).generate(full_text)
    
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    return fig, img_buf

def get_failsafe_keywords(titles):
    if not titles: return ["#데이터부족"]
    try:
        resp = ai_engine.generate_content(f"{titles}에서 제안서 소구점으로 쓸만한 구체적인 명사 5개만 #단어로 뽑아줘. '이슈, 트렌드, 분석' 금지.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = [w for w in re.findall(r'[가-힣]{2,}', " ".join(titles)) if len(w) > 2]
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

# --- 사이드바 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v14.7")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar (기존 유지)
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    # (이전 기능 동일 유지)
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 단백질쉐이크")
        if st.button("🚀 뉴스 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles)
                st.pyplot(fig)

# 2. 광고주 DB 관리 (표준화 로직 추가)
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일 업로드", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        st.session_state.history_db = normalize_db(df) # 🌟 칸 이름 자동 보정
        st.success("✅ 로드 완료 및 데이터 구조 최적화!")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력 (🌟 필터링 검색 기능 추가)
elif main
