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
st.set_page_config(page_title="AE Total Tool v14.8", layout="wide")

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

# 🌟 업종 카테고리 설정 (네이버 데이터랩 기준)
DETAILED_CATEGORIES = {
    "패션의류": ["여성의류", "남성의류", "언더웨어"],
    "패션잡화": ["신발", "가방", "쥬얼리", "시계"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어"],
    "디지털/가전": ["주방가전", "생활가전", "계절가전", "이미용가전"],
    "식품": ["건강식품", "다이어트식품", "음료", "신선식품", "가공식품"],
    "스포츠/레저": ["골프", "캠핑", "피트니스"],
    "생활/건강": ["주방용품", "욕실용품", "반려동물", "의료기기"]
}

# 세션 초기화 및 DB 열 이름 표준화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

def normalize_db(df):
    rename_map = {
        '날짜': ['날짜', '일자', '등록일', 'Date'],
        '광고주명': ['광고주명', '광고주', '업체명', 'Client'],
        '소통내용': ['소통내용', '내용', '상담내용', '소통'],
        '대분류': ['대분류', '카테고리', '업종'],
        '소분류': ['소분류', '세부카테고리', '세부업종']
    }
    new_cols = {}
    for standard, variations in rename_map.items():
        for col in df.columns:
            if col in variations: new_cols[col] = standard
    return df.rename(columns=new_cols)

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 22px; margin: 5px; background-color: #fff; border: 2px solid #FFB300; border-radius: 5px; font-weight: bold; color: #333; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

# 시각화 및 키워드 추출 함수
def create_cleaned_wc(text_data, height=600):
    if isinstance(text_data, pd.Series): text_list = text_data.dropna().astype(str).tolist()
    else: text_list = text_data
    full_text = " ".join(text_list)
    if not full_text.strip(): return None, None
    stop_words = ["뉴스", "제목", "기자", "지난", "이번", "통해", "함께", "대한", "관련", "위해", "있는", "합니다", "했다", "입니다", "경우", "제공", "사진", "오전", "오후", "오늘", "내일"]
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10', stopwords=set(stop_words), regexp=r"[가-힣]{2,}", max_words=80).generate(full_text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    return fig, img_buf

def get_failsafe_keywords(titles):
    if not titles: return ["#데이터부족"]
    try:
        resp = ai_engine.generate_content(f"{titles}에서 실무 제안용 핵심 단어 5개만 #단어로 뽑아줘. '이슈, 트렌드' 금지.")
        tags = re.findall(r'#\w+', resp.text)
        if len(tags) >= 5: return tags[:5]
    except: pass
    words = [w for w in re.findall(r'[가-힣]{2,}', " ".join(titles)) if len(w) > 2]
    return [f"#{w}" for w, c in Counter(words).most_common(5)]

# --- 사이드바 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v14.8")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 무릎 연골 영양제", key="n_k")
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
        s_keyword = c1.text_input("검색어 입력", key="s_k")
        if st.button("🔍 검색 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+이슈&hl=ko&gl=KR&ceid=KR:ko"
            titles = [i.title.get_text() for i in BeautifulSoup(requests.get(rss).text, 'xml').find_all('item')[:30]]
            if titles:
                st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in get_failsafe_keywords(titles)]), unsafe_allow_html=True)
                fig, _ = create_cleaned_wc(titles)
                st.pyplot(fig)

# 2. 광고주 DB 관리
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    up_f = st.file_uploader("💾 백업 파일 업로드", type=['xlsx'])
    if up_f:
        df = pd.read_excel(up_f, engine='openpyxl')
        st.session_state.history_db = normalize_db(df)
        st.success("✅ DB 로드 및 컬럼 자동 매칭 완료!")
    if not st.session_state.history_db.empty:
        towrite = BytesIO()
        st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button(label="📥 전체 DB 백업 다운로드", data=towrite.getvalue(), file_name=f"AE_Backup_{datetime.date.today()}.xlsx")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 직접 입력")
    db = st.session_state.history_db
    search_q = st.text_input("🔍 광고주 검색 필터", placeholder="업체명 일부를 입력하세요.")
    all_clients = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    filtered_clients = [c for c in all_clients if search_q in c] if search_q else all_clients

    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_date = c1.date_input("날짜", datetime.date.today())
        in_name_select = c2.selectbox("광고주 선택", ["직접 입력"] + filtered_clients)
        in_name_text = st.text_input("새 광고주명 (위 목록에 없을 때만 입력)")
        c3, c4 = st.columns(2)
        in_m_cat = c3.selectbox("대분류", list(DETAILED_CATEGORIES.keys()))
        in_s_cat = c4.selectbox("세부 분류", DETAILED_CATEGORIES[in_m_cat])
        in_content = st.text_area("소통 내용")
        if st.form_submit_button("💾 데이터 저장"):
            final_name = in_name_text if in_name_select == "직접 입력" else in_name_select
            new_row = pd.DataFrame({'날짜': [pd.to_datetime(in_date)], '광고주명': [final_name], '소통내용': [in_content], '대분류': [in_m_cat], '소분류': [in_s_cat]})
            st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
            st.success(f"✅ {final_name} 저장 성공!")

# 4. 내부 소통 이슈 리포트
elif main_menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    db = st.session_state.history_db
    search_rep = st.text_input("🔍 리포트 뽑을 광고주 검색", placeholder="업체명 검색")
    all_clients = sorted(db['광고주명'].dropna().unique().tolist()) if '광고주명' in db.columns else []
    filtered_rep = [c for c in all_clients if search_rep in c] if search_rep else all_clients
