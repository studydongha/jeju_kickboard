import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import math
import time
import itertools

# ==========================================
# 1. 하버사인 공식 (위경도 기반 실제 거리 계산 - 0초 컷)
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000 # 미터 단위 반환

# ==========================================
# 2. 실제 제주시청 인근 킥보드 거점 15곳 (Public Data)
# ==========================================
DEPOT = {"name": "제주시청 정문 (수거 트럭 출발)", "lat": 33.4996, "lng": 126.5312}

REAL_SPOTS = [
    {"name": "광양사거리 정류장", "lat": 33.5005, "lng": 126.5290},
    {"name": "CGV 제주점 앞", "lat": 33.4993, "lng": 126.5270},
    {"name": "신산공원 입구", "lat": 33.5015, "lng": 126.5350},
    {"name": "제주지방법원 앞", "lat": 33.4945, "lng": 126.5335},
    {"name": "제주동여중 앞", "lat": 33.5040, "lng": 126.5400},
    {"name": "제주소방서 교차로", "lat": 33.4912, "lng": 126.5360},
    {"name": "이도초등학교 인근", "lat": 33.4965, "lng": 126.5380},
    {"name": "제주중앙여고 앞", "lat": 33.4900, "lng": 126.5300},
    {"name": "보성시장 입구", "lat": 33.5020, "lng": 126.5250},
    {"name": "KAL 사거리", "lat": 33.5050, "lng": 126.5275},
    {"name": "제주시청 어울림마당", "lat": 33.4985, "lng": 126.5318},
    {"name": "제주한국병원 앞", "lat": 33.4998, "lng": 126.5220},
    {"name": "삼성혈 입구", "lat": 33.5032, "lng": 126.5321},
    {"name": "제주문예회관", "lat": 33.5038, "lng": 126.5375},
    {"name": "고마로 사거리", "lat": 33.5070, "lng": 126.5410}
]

# ==========================================
# 3. 경로 탐색 알고리즘
# ==========================================
def greedy_tsp(depot, spots):
    unvisited = spots.copy()
    current = depot
    path = []
    total_dist = 0
    
    while unvisited:
        nearest = min(unvisited, key=lambda spot: haversine(current['lat'], current['lng'], spot['lat'], spot['lng']))
        total_dist += haversine(current['lat'], current['lng'], nearest['lat'], nearest['lng'])
        path.append(nearest)
        current = nearest
        unvisited.remove(nearest)
    return path, total_dist

def brute_force_tsp(depot, spots):
    best_path = None
    min_dist = float('inf')
    
    for perm in itertools.permutations(spots):
        current_dist = 0
        current_pos = depot
        valid = True
        
        for next_spot in perm:
            current_dist += haversine(current_pos['lat'], current_pos['lng'], next_spot['lat'], next_spot['lng'])
            if current_dist >= min_dist: # 가지치기 (백트래킹)
                valid = False
                break
            current_pos = next_spot
            
        if valid and current_dist < min_dist:
            min_dist = current_dist
            best_path = list(perm)
            
    return best_path, min_dist

# ==========================================
# 4. Streamlit 웹 대시보드 UI
# ==========================================
st.set_page_config(page_title="제주 실사 라우팅 대시보드", layout="wide", page_icon="🌴")

st.sidebar.title("🌴 제주도 킥보드 관제")
st.sidebar.markdown("실제 제주시청 인근 데이터를 활용합니다.")

# 사이드바 컨트롤
num_kickboards = st.sidebar.slider("수거할 구역 수 (Scale)", min_value=3, max_value=15, value=8)
algo_mode = st.sidebar.selectbox("연산 알고리즘", ["탐욕 알고리즘 (Greedy TSP)", "완전 탐색 (Brute Force)"])
