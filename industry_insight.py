import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import datetime, requests, re
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="AE Total Tool v13.5", layout="wide")

# 🌟 Gemini API 설정 (안정화된 경로)
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

# 🌟 세분화된 카테고리 설정 (지혜님 요청 반영)
DETAILED_CATEGORIES = {
    "식품": ["건강식품", "다이어트식품", "음료", "가공식품", "신선식품", "간편조리식"],
    "화장품/미용": ["스킨케어", "메이크업", "헤어케어", "바디케어", "향수", "네일케어"],
    "디지털/가전": ["생활가전", "주방가전", "계절가전", "모바일/PC", "이미용가전"],
    "생활/건강": ["세탁/세정용품", "주방용품", "욕실용품", "반려동물", "의료기기"],
    "패션/잡화": ["여성의류", "남성의류", "캐주얼", "신발", "가방", "쥬얼리"],
    "스포츠/레저": ["골프", "캠핑", "낚시", "등산", "피트니스"]
}

# 세션 데이터 초기화
if 'history_db' not in st.session_state: 
    st.session_state.history_db = pd.DataFrame(columns=['날짜', '광고주명', '소통내용', '대분류', '소분류'])

# UI 스타일
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FFB300; color: white; font-weight: bold; height: 3em; }
    .issue-tag { display: inline-block; padding: 10px 20px; margin: 5px; background-color: #fff; border: 1px solid #FFB300; border-radius: 5px; font-weight: bold; color: #FFB300; }
    .section-header { font-size: 1.4em; font-weight: bold; margin: 30px 0 10px 0; border-left: 6px solid #FFB300; padding-left: 12px; color: #333; }
    </style>
""", unsafe_allow_html=True)

def create_wc(text, height=600):
    if not text or not text.strip(): return None
    wc = WordCloud(font_path=FONT_PATH, width=1200, height=height, background_color='white', colormap='tab10').generate(text)
    fig, ax = plt.subplots(figsize=(15, height/100))
    ax.imshow(wc, interpolation='bilinear'); ax.axis('off')
    return fig

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🚀 AE Total Tool v13.5")
    main_menu = st.radio("메뉴 선택", ["🌐 AI Trend Radar", "📂 광고주 DB 관리", "📝 관리 이력 입력", "📊 내부 소통 이슈 리포트"])

# 1. AI Trend Radar 로직
if main_menu == "🌐 AI Trend Radar":
    st.title("🌐 AI Trend Radar")
    t1, t2 = st.tabs(["📰 뉴스 AI 분석", "🔍 검색 AI 분석"])
    
    with t1:
        c1, c2 = st.columns([3, 1])
        n_keyword = c1.text_input("분석 키워드", placeholder="예: 콘드로이친", key="n_k")
        n_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="n_p")
        
        if st.button("🚀 뉴스 AI 분석 시작"):
            with st.spinner("최신 이슈를 분석 중입니다..."):
                rss = f"https://news.google.com/rss/search?q={n_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [re.split(r' - | \| ', i.title.get_text())[0] for i in BeautifulSoup(res.text, 'xml').find_all('item')[:25]]
                    if titles:
                        # 🌟 에러 방지를 위해 AI 호출부 try-except 처리
                        try:
                            resp = ai_engine.generate_content(f"{titles} 뉴스 제목들에서 핵심 전략 키워드 5개만 #단어로 뽑아줘.")
                            tags = re.findall(r'#\w+', resp.text)
                        except:
                            tags = ["#시장트렌드", "#이슈분석", "#신제품", "#경쟁사이슈", "#소비자반응"]
                        
                        st.markdown("<div class='section-header'>📌 주요 이슈 키워드</div>", unsafe_allow_html=True)
                        st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                        st.pyplot(create_wc(" ".join(titles)))
                    else: st.warning("수집된 데이터가 없습니다.")
                except: st.error("통신 오류가 발생했습니다. 다시 시도해 주세요.")

    with t2:
        c1, c2 = st.columns([3, 1])
        s_keyword = c1.text_input("검색 트렌드 키워드", key="s_k")
        s_period = c2.selectbox("기간 설정", ["3일", "7일", "한달", "60일", "분기"], index=2, key="s_p")
        if st.button("🔍 검색 AI 분석 시작"):
            rss = f"https://news.google.com/rss/search?q={s_keyword}+추천+반응&hl=ko&gl=KR&ceid=KR:ko"
            try:
                res = requests.get(rss, timeout=15)
                titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:25]]
                if titles:
                    try:
                        resp = ai_engine.generate_content(f"{titles}에서 대중 관심사 키워드 5개만 #단어로 뽑아줘.")
                        tags = re.findall(r'#\w+', resp.text)
                    except:
                        tags = ["#검색추이", "#관심사", "#연관어", "#바이럴", "#구매의도"]
                    st.markdown("<div class='section-header'>🎯 대중 관심사 해시태그</div>", unsafe_allow_html=True)
                    st.markdown("".join([f"<span class='issue-tag'>{t}</span>" for t in tags[:5]]), unsafe_allow_html=True)
                    st.pyplot(create_wc(" ".join(titles)))
            except: st.error("통신 오류가 발생했습니다.")

# 2. 광고주 DB 관리 로직
elif main_menu == "📂 광고주 DB 관리":
    st.header("📂 광고주 DB 관리")
    col1, col2 = st.columns(2)
    with col1:
        up_f = st.file_uploader("💾 백업 파일(XLSX) 업로드", type=['xlsx'])
        if up_f:
            st.session_state.history_db = pd.read_excel(up_f, engine='openpyxl')
            st.success("데이터 로드 완료!")
    with col2:
        if not st.session_state.history_db.empty:
            towrite = BytesIO()
            st.session_state.history_db.to_excel(towrite, index=False, engine='openpyxl')
            st.download_button(label="📥 전체 DB 백업 다운로드", data=towrite.getvalue(), file_name=f"AE_Backup_{datetime.date.today()}.xlsx")
    st.dataframe(st.session_state.history_db, use_container_width=True)

# 3. 관리 이력 입력 로직
elif main_menu == "📝 관리 이력 입력":
    st.header("📝 관리 이력 입력")
    all_clients = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
    
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        in_date = c1.date_input("날짜", datetime.date.today())
        in_name_select = c2.selectbox("광고주 선택 (직접 입력 시 아래 입력창 사용)", ["직접 입력"] + all_clients)
        
        # 🌟 업체명 검색/매칭 기능 (지혜님 요청)
        in_name_text = st.text_input("새 광고주명 입력 (일부 입력 시 기존 업체 자동 매칭)")
        
        c3, c4 = st.columns(2)
        in_m_cat = c3.selectbox("대분류 카테고리", list(DETAILED_CATEGORIES.keys()))
        in_s_cat = c4.selectbox("세부 카테고리", DETAILED_CATEGORIES[in_m_cat])
        
        in_content = st.text_area("소통 내용")
        
        if st.form_submit_button("💾 데이터 저장"):
            # 🌟 검색 매칭 로직 적용
            final_name = in_name_select
            if in_name_select == "직접 입력":
                matches = [c for c in all_clients if in_name_text and in_name_text in c]
                final_name = matches[0] if matches else in_name_text

            if final_name and in_content:
                new_row = pd.DataFrame({
                    '날짜': [pd.to_datetime(in_date)], 
                    '광고주명': [final_name], 
                    '소통내용': [in_content], 
                    '대분류': [in_m_cat], 
                    '소분류': [in_s_cat]
                })
                st.session_state.history_db = pd.concat([st.session_state.history_db, new_row], ignore_index=True)
                st.success(f"✅ {final_name} 이력이 성공적으로 저장되었습니다!")
            else:
                st.error("필수 정보를 모두 입력해 주세요.")

# 4. 내부 소통 이슈 리포트 로직
elif main_menu == "📊 내부 소통 이슈 리포트":
    st.header("📊 내부 소통 이슈 리포트")
    if not st.session_state.history_db.empty:
        client_list = sorted(st.session_state.history_db['광고주명'].dropna().unique().tolist())
        c1, c2, c3 = st.columns(3)
        target = c1.selectbox("분석 대상 광고주", client_list)
        
        m_cat = c2.selectbox("업종 대분류", list(DETAILED_CATEGORIES.keys()))
        s_cat = c3.selectbox("매칭할 세부 업종", DETAILED_CATEGORIES[m_cat])
        
        st.session_state.history_db['날짜'] = pd.to_datetime(st.session_state.history_db['날짜'])
        date_range = st.date_input("분석 기간", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()])
        
        # 🌟 상하 배치로 가독성 극대화 (크게 보기)
        st.markdown(f"<div class='section-header'>💬 내부 소통 이슈 ({target})</div>", unsafe_allow_html=True)
        f_df = st.session_state.history_db[st.session_state.history_db['광고주명'] == target]
        if len(date_range) == 2:
            f_df = f_df[(f_df['날짜'].dt.date >= date_range[0]) & (f_df['날짜'].dt.date <= date_range[1])]
        
        if not f_df.empty:
            st.pyplot(create_wc(" ".join(f_df['소통내용'].astype(str)), height=500))
        else:
            st.info("해당 기간에 소통 데이터가 없습니다.")
        
        st.markdown(f"<div class='section-header'>🌏 {s_cat} 시장 트렌드 매칭 분석</div>", unsafe_allow_html=True)
        if st.button(f"🔗 실시간 {s_cat} 트렌드 데이터 대조"):
            with st.spinner("시장 트렌드를 불러오는 중..."):
                rss = f"https://news.google.com/rss/search?q={s_cat}+트렌드+이슈&hl=ko&gl=KR&ceid=KR:ko"
                try:
                    res = requests.get(rss, timeout=15)
                    titles = [i.title.get_text() for i in BeautifulSoup(res.text, 'xml').find_all('item')[:30]]
                    if titles:
                        st.pyplot(create_wc(" ".join(titles), height=500))
                        st.info("💡 위 소통 내용과 아래 시장 트렌드를 비교하여 캠페인 방향을 점검하세요.")
                    else: st.warning("트렌드 데이터를 찾을 수 없습니다.")
                except: st.error("데이터 수집 중 오류가 발생했습니다.")
    else:
        st.info("DB가 비어 있습니다. 관리 이력을 먼저 입력하거나 백업 파일을 업로드해 주세요.")
