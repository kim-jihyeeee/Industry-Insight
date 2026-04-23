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
st.set_page_config(page_title="AE Total Tool v18.5", layout="wide")
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

# 🌟 네이버 데이터랩 쇼핑 인사이트 기준 중분류 카테고리 (풀세팅 유지)
CATS = {
    "패션의류": ["여성의류", "남성의류", "언더웨어/잠옷", "스포츠의류", "아동의류"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계", "선글라스/안경테", "지갑/벨트"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "뷰티소품"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전", "PC/노트북", "음향기기"],
    "식품": ["건강식품", "다이어트식품", "음료", "신선식품", "가공식품", "커피/차"],
    "스포츠/레저": ["골프", "캠핑", "피트니스/요가", "등산", "낚시", "자전거", "수영"],
    "생활/건강": ["주방용품", "욕실용품", "반려동물", "의료기기", "생활용품", "세탁/세정용품"],
    "출산/육아": ["분유/기저귀", "수유용품", "유모차/카시트", "아기물티슈", "임부복/용품"]
}

if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

# 공통 유틸리티
def create_wc(data, h=500):
    txt = " ".join(data.dropna().astype(str)) if isinstance(data, pd.Series) else " ".join(data)
    if not txt.strip(): return None, None
    sw = ["뉴스", "제목", "기자", "통해", "대한", "관련", "위해", "있는", "지난", "이번"]
    wc = WordCloud(font_path=F_PATH, width=1200, height=h, background_color='white', colormap='tab10', stopwords=set(sw), regexp=r"[가-힣]{2,}").generate(txt)
    fig, ax = plt.subplots(figsize=(15, h/100)); ax.imshow(wc); ax.axis('off')
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

# --- 사이드바 및 앱 이름 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v18.5")
    menu = st.radio("메뉴", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar (키워드 5개 복구 완료)
if menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 분석", "🔍 검색 분석"])
    for i, t in enumerate([t1, t2]):
        with t:
            c1, c2 = st.columns([3, 1])
            k = c1.text_input(f"{['뉴스', '검색어'][i]} 입력", key=f"k{i}")
            p = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=3, key=f"p{i}")
            if st.button(f"🚀 {['뉴스', '검색'][i]} 분석 시작", key=f"b{i}"):
                q = k if i==0 else f"{k}+추천+이슈"
                res = requests.get(f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko")
                titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                if titles:
                    st.write(" ".join([f"**{tag}**" for tag in get_tags(titles)]))
                    fig, _ = create_wc(titles); st.pyplot(fig)

# 2. DB 관리
elif menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up = st.file_uploader("💾 XLSX 업로드", type=['xlsx'])
    if up:
        df = pd.read_excel(up, engine='openpyxl')
        df.columns = [{'광고주':'광고주명','업체명':'광고주명','내용':'소통내용'}.get(c, c) for c in df.columns]
        st.session_state.history_db = df
    if not st.session_state.history_db.empty:
        st.dataframe(st.session_state.history_db, use_container_width=True)
        tow = BytesIO(); st.session_state.history_db.to_excel(tow, index=False)
        st.download_button("📥 DB 백업 다운로드", tow.getvalue(), "AE_DB.xlsx")

# 3. 이력 입력 (스마트 필터링 유지)
elif menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 직접 입력")
    db = st.session_state.history_db
    all_c = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    sq = st.text_input("🔍 광고주 검색 필터", placeholder="'그린' 등 입력")
    flist = [c for c in all_c if sq in c] if sq else all_c
    with st.form("in_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dt = c1.date_input("날짜", datetime.date.today())
        sel = c2.selectbox("광고주 선택", ["직접 입력"] + flist)
        txt = st.text_input("새 광고주명 (목록에 없을 때)")
        m = st.selectbox("대분류 (네이버 기준)", list(CATS.keys()))
        s = st.selectbox("세부분류", CATS[m])
        cont = st.text_area("소통 내용")
        if st.form_submit_button("💾 데이터 저장"):
            fn = txt if sel == "직접 입력" else sel
            if not fn and sq: fn = flist[0] if flist else sq
            new = pd.DataFrame({'날짜':[pd.to_datetime(dt)], '광고주명':[fn], '소통내용':[cont], '대분류':[m], '소분류':[s]})
            st.session_state.history_db = pd.concat([st.session_state.history_db, new], ignore_index=True)
            st.success(f"✅ {fn} 저장 성공!")

# 4. 리포트 (에러 해결 및 상하 배치)
elif menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    db = st.session_state.history_db
    if not db.empty and '광고주명' in db.columns:
        c1, c2, c3 = st.columns(3)
        ts = c1.text_input("🔍 분석 광고주 검색", key="search_rep")
        all_c_sorted = sorted(db['광고주명'].dropna().unique())
        tlist = [c for c in all_c_sorted if ts in c] if ts else all_c_sorted
        target = c1.selectbox("최종 분석 대상 선택", tlist)
        
        m = c2.selectbox("업종 대분류 선택", list(CATS.keys()))
        s = c3.selectbox("업종 세부분류 선택", CATS[m])
        dr = st.date_input("분석 기간 설정", [datetime.date.today()-datetime.timedelta(days=30), datetime.date.today()])
        
        st.markdown(f"### 💬 {target} 소통 이슈")
        f_df = db[db['광고주명'] == target].copy()
        f_df['날짜'] = pd.to_datetime(f_df['날짜'], errors='coerce')
        if len(dr) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= dr[0]) & (f_df['날짜'].dt.date <= dr[1])]
        
        if not f_df.empty:
            fig, buf = create_wc(f_df['소통내용']); st.pyplot(fig)
            st.download_button("🖼️ 이미지 저장", buf.getvalue(), f"{target}_WC.png", key="d1")
            
        st.markdown(f"### 🌏 {s} 시장 트렌드 매칭")
        if st.button("🔗 실시간 트렌드 불러오기"):
            rss = f"https://news.google.com/rss/search?q={s}+트렌드&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss)
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            fig, buf = create_wc(titles); st.pyplot(fig)
            st.download_button("🖼️ 시장 이미지 저장", buf.getvalue(), f"{s}_Trend.png", key="d2")
    else: st.info("📂 DB를 먼저 업로드해 주세요.")
