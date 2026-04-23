import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai
from collections import Counter

st.set_page_config(page_title="AE Total Tool v15.5", layout="wide")

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

DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "스포츠의류", "아동의류", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "지갑/벨트", "모자", "패션소품"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어", "뷰티소품"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "영상가전", "PC/노트북", "음향기기"],
    "식품": ["건강식품", "다이어트식품", "음료", "커피/차", "가공식품", "신선식품"],
    "스포츠/레저": ["골프", "캠핑", "피트니스/요가", "등산", "낚시", "자전거", "수영"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기", "문구/사무용품"],
    "출산/육아": ["분유/기저귀", "임부복/용품", "유모차/카시트", "아기물티슈", "목욕용품"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_column_names(df):
    rename_map = {'날짜': ['날짜', '일자', 'Date'], '광고주명': ['광고주명', '광고주', '업체명'], '소통내용': ['소통내용', '내용', '소통']}
    new_cols = {col: standard for standard, variations in rename_map.items() for col in df.columns if col in variations}
    return df.rename(columns=new_cols)

st.markdown("<style>.stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; }.issue-tag { display: inline-block; padding: 8px 18px; margin: 5px; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; }.section-header { font-size: 1.4em; font-weight: bold; margin: 20px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; }</style>", unsafe_allow_html=True)

def create_cleaned_wc(text_data, height=600):
    text_list = text_data.dropna().astype(str).tolist() if isinstance(text_data, pd.Series) else text_data
    full_text = " ".join(text_list)
    if not full_text.strip(): return None, None
    stop = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번"]
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', stopwords=set(stop), regexp=r"[가-힣]{2,}", max_words=80).generate(full_text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    buf = BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight')
    return fig, buf

def get_failsafe_keywords(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 제안용 핵심 명사 5개만 #단어로 뽑아줘.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = re.findall(r'[가-힣]{2,}', " ".join(titles))
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

with st.sidebar:
    st.title("🚀 AE Total Tool v15.5")
    main_menu = st.radio("메뉴", ["🌐 AI Trend Radar", "📂 DB 관리", "📝 이력 입력", "📊 이슈 리포트"])

if main_menu == "🌐 AI Trend Radar":
    t1, t2 = st.tabs(["📰 뉴스 분석", "🔍 검색 분석"])
    with t1:
        c1, c2 = st.columns([3, 1])
        n_k = c1.text_input("키워드", placeholder="무릎 연골")
        n_p = c2.selectbox("기간", ["3일", "7일", "한달", "60일", "분기"], index=3)
        if st.button("🚀 뉴스 분석"):
            rss = f"https://news.google.com/rss/search?q={n_k}&hl=ko&gl=KR&ceid=KR:ko"
            titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles); st.pyplot(fig)
    with t2:
        c1, c2 = st.columns([3, 1])
        s_k = c1.text_input("검색어", key="sk")
        s_p = c2.selectbox("기간", ["3일", "7일", "한달", "60일", "분기"], index=3, key="sp")
        if st.button("🔍 검색 분석"):
            rss = f"https://news.google.com/rss/search?q={s_k}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles); st.pyplot(fig)

elif main_menu == "📂 DB 관리":
    up = st.file_uploader("💾 XLSX 업로드", type=['xlsx'])
    if up:
        st.session_state.history_db = normalize_column_names(pd.read_excel(up))
        st.success("로드 완료!")
    if not st.session_state.history_db.empty:
        out = BytesIO(); st.session_state.history_db.to_excel(out, index=False)
        st.download_button("📥 DB 다운로드", out.getvalue(), "AE_Backup.xlsx")
    st.dataframe(st.session_state.history_db, use_container_width=True)

elif main_menu == "📝 이력 입력":
    db = st.session_state.history_db
    clients = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    search = st.text_input("🔍 광고주 검색", placeholder="'그린' 등 입력")
    filtered = [c for c in clients if search in c] if search else clients
    with st.form("in_form", clear_on
