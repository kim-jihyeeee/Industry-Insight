import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai
from collections import Counter

# 1. 설정 및 AI 초기화
st.set_page_config(page_title="AE Total Tool v22.2", layout="wide")
API_KEY = "AQ.Ab8RN6Lc9LYyyyi-oE7eVOZfjfe8AKJIQ8u3SnPmUce-LjoZRw"

@st.cache_resource
def init_ai():
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    except: return None

ai_engine = init_ai()

@st.cache_data
def load_font():
    try:
        res = requests.get("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf")
        with open("nanum_font.ttf", "wb") as f: f.write(res.content)
        return "nanum_font.ttf"
    except: return None

F_PATH = load_font()

# 🌟 카테고리 (네이버 쇼핑 인사이트 기준 풀세팅)
CATS = {
    "패션의류": ["여성의류", "남성의류", "스포츠의류", "언더웨어/잠옷"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "선글라스/안경테"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전", "PC/노트북"],
    "식품": ["건강식품", "다이어트식품", "음료", "신선식품", "가공식품", "커피/차"],
    "스포츠/레저": ["골프", "캠핑", "피트니스", "등산", "낚시", "자전거"],
    "생활/건강": ["주방용품", "욕실용품", "반려동물", "의료기기", "생활용품"],
    "출산/육아": ["분유/기저귀", "수유용품", "유모차/카시트", "아기물티슈"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def fix_col(df):
    m = {'날짜':['날짜','일자','Date'], '광고주명':['광고주명','광고주','업체명'], '소통내용':['소통내용','내용','소통']}
    new = {}
    for k, v in m.items():
        for c in df.columns:
            if str(c).strip() in v: new[c] = k
    return df.rename(columns=new)

# 🌟 워드클라우드 (노이즈 정제 강화)
def create_wc(data, h=500):
    txt = " ".join(data.dropna().astype(str)) if isinstance(data, pd.Series) else " ".join(data)
    if not txt.strip(): return None, None
    sw = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번", "제공", "사진", "오전", "오후", "최근", "대해", "따라", "포함"]
    wc = WordCloud(font_path=F_PATH, width=1200, height=h, background_color='white', colormap='tab10', stopwords=set(sw), regexp=r"[가-힣]{2,}", max_words=60).generate(txt)
    fig, ax = plt.subplots(figsize=(15, h/100)); ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    buf = BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight')
    return fig, buf

def get_tags(titles):
    try:
        resp = ai_engine.generate_content(f"{titles}에서 실무 제안용 핵심 명사 5개만 #단어로 뽑아줘.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = re.findall(r'[가-힣]{2,}', " ".join(titles))
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

# --- 메뉴 ---
menu = st.sidebar.radio("메뉴", ["🌐 Radar", "📂 DB 관리", "📝 이력 입력", "📊 리포트"])

if menu == "🌐 Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 분석", "🔍 검색 분석"])
    for i, t in enumerate([t1, t2]):
        with t:
            c1, c2 = st.columns([3, 1])
            k = c1.text_input(f"{['뉴스', '검색어'][i]} 입력", key=f"k{i}")
            p = c2.selectbox("기간", ["3일", "7일", "한달", "60일", "분기"], index=3, key=f"p{i}")
            if st.button(f"🚀 {['뉴스', '검색'][i]} 분석 시작", key=f"b{i}"):
                q = k if i==0 else f"{k}+추천+이슈"
                res = requests.get(f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko")
                titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                if titles:
                    st.write(" ".join([f"**{tag}**" for tag in get_tags(titles)]))
                    fig, _ = create_wc(titles); st.pyplot(fig)

elif menu == "📂 DB 관리":
    st.header("📂 DB 관리")
    up = st.file_uploader("XLSX 업로드", type=['xlsx'])
    if up:
        st.session_state.history_db = fix_col(pd.read_excel(up, engine='openpyxl'))
        st.success("로드 완료")
    if not st.session_state.history_db.empty:
        st.dataframe(st.session_state.history_db, use_container_width=True)
        tow = BytesIO(); st.session_state.history_db.to_excel(tow, index=False)
        st.download_button("📥 다운로드", tow.getvalue(), "AE_DB.xlsx")

elif menu == "📝 이력 입력":
    st.header("📝 관리 이력 입력")
    db = st.session_state.history_db
    all_c = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    sq = st.text_input("🔍 광고주 검색 필터", placeholder="'그린' 등 입력")
    flist = [c for c in all_c if sq in c] if sq else all_c
    with st.form("in_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dt, sel = c1.date_input("날짜", datetime.date.today()), c2.selectbox("광고주 선택", ["직접 입력"] + flist)
        txt, m = st.text_input("새 광고주명"), st.selectbox("대분
