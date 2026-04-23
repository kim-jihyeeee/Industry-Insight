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
st.set_page_config(page_title="AE Total Tool v15.5", layout="wide")

# Gemini API 설정
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

# 🌟 네이버 데이터랩 쇼핑 인사이트 기준 전체 카테고리
DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "스포츠의류", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "지갑/벨트", "모자"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전", "PC/노트북"],
    "식품": ["건강식품", "다이어트식품", "음료", "커피/차", "가공식품", "신선식품"],
    "스포츠/레저": ["골프", "캠핑", "피트니스/요가", "등산", "낚시", "자전거"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기", "생활용품"],
    "출산/육아": ["분유/기저귀", "수유용품", "유모차/카시트", "아기물티슈", "목욕용품"]
}

# 세션 초기화 및 DB 표준화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_db(df):
    rename = {'날짜':['날짜','일자','Date'], '광고주명':['광고주명','광고주','업체명'], '소통내용':['소통내용','내용','소통']}
    new_cols = {}
    for std, vars in rename.items():
        for col in df.columns:
            if col in vars: new_cols[col] = std
    return df.rename(columns=new_cols)

# 공통 로직
def create_wc(text_data, h=600):
    txt = " ".join(text_data.dropna().astype(str)) if isinstance(text_data, pd.Series) else " ".join(text_data)
    if not txt.strip(): return None, None
    sw = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번"]
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=h, background_color='white', colormap='tab10', stopwords=set(sw), regexp=r"[가-힣]{2,}").generate(txt)
    fig, ax = plt.subplots(figsize=(15, h/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    buf = BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight')
    return fig, buf

def get_tags(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 실무 제안용 핵심 명사 5개만 #단어로 뽑아줘. 이슈/트렌드 금지.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    return [f"#{w}" for w, c in Counter(re.findall(r'[가-힣]{2,}', " ".join(titles))).most_common(5)]

# --- 사이드바 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v15.5")
    menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar
if menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    with t1:
        c1, c2 = st.columns([3, 1])
        n_k = c1.text_input("분석 키워드", placeholder="무릎 연골")
        n_p = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="nkp")
        if st.button("🚀 뉴스 분석 시작"):
            res = requests.get(f"https://news.google.com/rss/search?q={n_k}&hl=ko&gl=KR&ceid=KR:ko")
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_tags(titles)]), unsafe_allow_html=True)
                f, _ = create_wc(titles); st.pyplot(f)
    with t2:
        c1, c2 = st.columns([3, 1])
        s_k = c1.text_input("검색어 입력", key="sk")
        s_p = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key="skp")
        if st.button("🔍 검색 AI 분석 시작"):
            res = requests.get(f"https://news.google.com/rss/search?q={s_k}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko")
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_tags(titles)]), unsafe_allow_html=True)
                f, _ = create_wc(titles); st.pyplot(f)

# 2. DB 관리
elif menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("XLSX 업로드", type=['xlsx'])
    if up_f:
        st.session_state.history_db = normalize_db(pd.read_excel(up_f, engine='openpyxl'))
        st.success("✅ 로드 완료!")
    if not st.session
