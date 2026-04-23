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
st.set_page_config(page_title="AE Total Tool v14.4", layout="wide")

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

# 세분화된 카테고리
DETAILED_CATEGORIES = {
    "식품": ["건강식품", "다이어트식품", "음료", "가공식품", "신선식품", "간편조리식"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["생활가전", "주방가전", "계절가전", "모바일/PC", "이미용가전"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기"],
    "패션/잡화": ["여성의류", "남성제품", "캐주얼", "신발", "가방", "쥬얼리"],
    "스포츠/레저": ["골프", "캠핑", "낚시", "등산", "피트니스"]
}

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

# 핵심 로직 함수들
def get_failsafe_keywords(titles):
    if not titles: return ["#데이터부족"]
    try:
        resp = ai_engine.generate_content(f"{titles}에서 제안서용 핵심 키워드 5개만 #단어로 뽑아줘. 이슈, 트렌드 같은 뻔한 단어 제외.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    combined_text = " ".join(titles)
    words = re.findall(r'[가-힣]{2,}', combined_text)
    counts = Counter(words)
    return [f"#{w}" for w, c in counts.most_common(5)]

def create_cleaned_wc(text_list, height=600):
    full_text = " ".join(text_list)
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', regexp=r"[가-힣]{2,}").generate(full_text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v14.4")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar 복구
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 무릎 연골", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="n_p")
        if st.button("🚀 전략 뉴스 분석 시작"):
            with st.spinner("데이터 분석 중..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(rss, timeout=15)
                titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                if titles:
                    tags = get_failsafe_keywords(titles)
                    st.markdown("<div class='section-header'>📌 시장 실시간 핵심 키워드</div>", unsafe_allow_html=True)
                    st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                    st.pyplot(create_cleaned_wc(titles))
    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="s_p")
        if st.button("🔍 시장 니즈 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(rss, timeout=15)
            titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
            if titles:
                tags = get_failsafe_keywords(titles)
                st.markdown("<div class='section-header'>🎯 대중 관심사 실시간 태그</div>", unsafe_allow_html=True)
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags]), unsafe_allow_html=True)
                st.pyplot(create_cleaned_wc(titles))

# 2. DB 관리 복구
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일 업로드", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        rename_map = {'광고주': '광고주명', '업체명': '광고주명', '내용': '소통내용'}
        df.columns = [rename_map.get(c, c) for c in df.columns]
        st.session_state.history_db = df
        st.success("✅ 데이터 로드 완료!")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력 복구
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 직접 입력")
    db = st.session_state.history_db
    client_list = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_date = c1.date_input("날짜", datetime.date.today())
        in_name_select = c2.selectbox("광고주 선택", ["직접 입력"] + client_list)
        in_name_text = st.text_input("새 광고주명 입력")
        c3, c4 = st.columns(2)
        in_m_cat = c3.selectbox("대분류", list(DETAILED_CATEGORIES.keys()))
        in_s_cat = c4.selectbox("세부 분류", DETAILED_CATEGORIES[in_m_cat])
        in_content = st.text_area("소통 내용")
        if st.form_submit_button("💾 데이터 저장"):
            final_name = in_name_text if in_name_select == "직접 입력" else in_name_select
            new_row = pd.DataFrame({'날짜': [pd.to_datetime(in_date)], '광고주명': [final_name], '소통내용': [in_content], '대분류': [in_m_cat], '소분류': [in_s_cat]})
            st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
            st.success("저장 완료!")

# 4. 리포트 화면 복구
elif main_menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    db = st.session_state.history_db
    if not db.empty and '광고주명' in db.columns:
        client_list = sorted(db['광고주명'].dropna().unique().tolist())
        c1, c2, c3 = st.columns(3)
        target = c1.selectbox("광고주 선택", client_list)
        m_cat = c2.selectbox("업종 대분류", list(DETAILED_CATEGORIES.keys()))
        s_cat = c3.selectbox("업종 세분류", DETAILED_CATEGORIES[m_cat])
        
        st.markdown(f"<div class='section-header'>💬 내부 소통 이슈 ({target})</div>", unsafe_allow_html=True)
        f_df = db[db['광고주명'] == target]
        if not f_df.empty:
            st.pyplot(create_cleaned_wc(f_df['소통내용'].astype(str), height=500))
        
        st.markdown(f"<div class='section-header'>🌏 {s_cat} 시장 트렌드 매칭</div>", unsafe_allow_html=True)
        if st.button(f"🔗 {s_cat} 트렌드 불러오기"):
            rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드&hl=ko&gl=KR&ceid=KR:ko"
            titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
            st.pyplot(create_cleaned_wc(titles, height=500))
    else:
        st.info("데이터가 없습니다. DB 관리에서 파일을 먼저 업로드해주세요.")
