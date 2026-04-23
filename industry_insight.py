import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 설정 및 AI 초기화
st.set_page_config(page_title="AE Total Tool v17.0", layout="wide")
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

# 공통 함수
def create_wc(data, h=500):
    txt = " ".join(data.dropna().astype(str)) if isinstance(data, pd.Series) else " ".join(data)
    if not txt.strip(): return None
    sw = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는"]
    wc = WordCloud(font_path=F_PATH, width=1200, height=h, background_color='white', stopwords=set(sw), regexp=r"[가-힣]{2,}").generate(txt)
    fig, ax = plt.subplots(figsize=(15, h/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    buf = BytesIO(); fig.savefig(buf, format='png', bbox_inches='tight')
    return fig, buf

# --- 사이드바 및 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v17.0") # 🌟 앱 이름 복구
    menu = st.radio("메뉴", ["🌐 AI Trend Radar", "📂 광고주 DB 관리"])

# 1. AI Trend Radar
if menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    for i, t in enumerate([t1, t2]):
        with t:
            c1, c2 = st.columns([3, 1])
            k = c1.text_input(f"{['뉴스', '검색어'][i]} 입력", key=f"k{i}")
            p = c2.selectbox("기간", ["3일", "7일", "한달", "60일", "분기"], index=3, key=f"p{i}")
            if st.button(f"🚀 {['뉴스', '검색'][i]} 분석 시작", key=f"b{i}"):
                q = k if i==0 else f"{k}+추천+이슈"
                try:
                    res = requests.get(f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko")
                    titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                    if titles:
                        # 🌟 괄호 오타 수정 완료
                        fig, _ = create_wc(titles); st.pyplot(fig)
                    else: st.warning("데이터가 없습니다.")
                except: st.error("통신 장애 발생")

# 2. DB 관리
elif menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up = st.file_uploader("💾 XLSX 업로드", type=['xlsx'])
    if up:
        df = pd.read_excel(up, engine='openpyxl')
        # 간단 표준화
        df.columns = [{'광고주':'광고주명','업체명':'광고주명','내용':'소통내용'}.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("✅ 로드 완료!")
    if 'history_db' in st.session_state and not st.session_state.history_db.empty:
        st.dataframe(st.session_state.history_db, use_container_width=True)
        towrite = BytesIO(); st.session_state.history_db.to_excel(towrite, index=False)
        st.download_button("📥 백업 다운로드", towrite.getvalue(), "AE_DB.xlsx")
    else: st.info("📂 XLSX 파일을 먼저 업로드해 주세요.")
