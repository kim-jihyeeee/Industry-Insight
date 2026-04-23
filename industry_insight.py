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
st.set_page_config(page_title="AE Total Tool v15.2", layout="wide")

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

# 🌟 네이버 데이터랩(쇼핑 인사이트) 기준 정교화된 카테고리
DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "언더웨어/잠옷", "스포츠의류", "아동의류"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "지갑/벨트", "모자"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어", "남성화장품"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "영상가전", "이미용가전", "PC/노트북", "음향기기"],
    "식품": ["건강식품", "다이어트식품", "음료", "커피/차", "과자/베이커리", "가공식품", "신선식품"],
    "스포츠/레저": ["골프", "캠핑", "피트니스/요가", "등산", "낚시", "자전거", "수영"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기", "생활용품", "수구/공구"],
    "출산/육아": ["분유/기저귀", "임부복/용품", "수유용품", "유모차/카시트", "아기물티슈"]
}

# 세션 초기화 및 DB 표준화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_column_names(df):
    rename_map = {
        '날짜': ['날짜', '일자', 'Date', '등록일'],
        '광고주명': ['광고주명', '광고주', '업체명', 'Client'],
        '소통내용': ['소통내용', '내용', '소통', '상담내용']
    }
    new_cols = {}
    for standard, variations in rename_map.items():
        for col in df.columns:
            if col in variations:
                new_cols[col] = standard
    return df.rename(columns=new_cols)

# 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 8px 18px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 시각화 및 키워드 추출
def create_cleaned_wc(text_data, height=600):
    if isinstance(text_data, pd.Series): text_list = text_data.dropna().astype(str).tolist()
    else: text_list = text_data
    full_text = " ".join(text_list)
    if not full_text.strip(): return None, None
    stop_words = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번"]
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', stopwords=set(stop_words), regexp=r"[가-힣]{2,}", max_words=80).generate(full_text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    return fig, img_buf

def get_failsafe_keywords(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 실무 제안용 핵심 명사 5개만 #단어로 뽑아줘. 이슈, 트렌드 단어 금지.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = [w for w in re.findall(r'[가-힣]{2,}', " ".join(titles)) if len(w) > 1]
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

# --- 사이드바 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v15.2")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar (키워드 추천 기능 복구)
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("뉴스 분석 키워드", placeholder="예: 무릎 연골")
        n_period = c2.selectbox("뉴스 기간", ["3일", "7일", "한달", "60일", "분기"], index=3, key="n_p")
        if st.button("🚀 뉴스 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss, timeout=15)
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles)
                st.pyplot(fig)
    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("검색 기간", ["3일", "7일", "한달", "60일", "분기"], index=3, key="s_p")
        if st.button("🔍 검색 AI 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss, timeout=15)
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            if titles:
                # 🌟 [복구] 검색 분석에서도 5개 키워드 추천 노출
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles)
                st.pyplot(fig)

# 2. 광고주 DB 관리 (기존 유지)
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일 업로드 (XLSX)", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        st.session_state.history_db = normalize_column_names(df)
        st.success("✅ DB 로드 완료!")
    if not st.session_state.history_db.empty:
        towrite = BytesIO()
        st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("📥 전체 DB 백업 다운로드", towrite.getvalue(), f"AE_Backup_{datetime.date.today()}.xlsx")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력 (스마트 검색 유지 + 카테고리 전체 표기)
elif main_menu == "📝 관리 이
