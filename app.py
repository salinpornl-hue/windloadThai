import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# ==========================================
# ฐานข้อมูลและฟังก์ชันคณิตศาสตร์ (มยผ. 1311-50 / 1302)
# ==========================================
PROVINCE_V = {
    "กรุงเทพฯ / นนทบุรี / ปทุมธานี / สมุทรปราการ / สมุทรสาคร (25 m/s)": 25.0,
    "ชลบุรี / ระยอง / จันทบุรี / ตราด (30 m/s)": 30.0,
    "ภูเก็ต / พังงา / กระบี่ (27 m/s)": 27.0,
    "เชียงใหม่ / เชียงราย / พิษณุโลก / แม่ฮ่องสอน (25 m/s)": 25.0,
    "นครราชสีมา / ขอนแก่น / อุดรธานี / อุบลราชธานี (25 m/s)": 25.0,
    "สงขลา / สุราษฎร์ธานี / นครศรีธรรมราช (25 m/s)": 25.0,
    "🛠️ กำหนดค่าความเร็วลมเอง (Manual Input)": 25.0
}

def calculate_q(V):
    return (0.5 * 1.25 * (V ** 2)) / 9.80665

def get_Ce_details(z, exposure):
    z_eff = max(z, 6.0) 
    if 'A' in exposure: alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure: alpha, min_val, max_val = 0.28, 0.7, 1.2
    else: alpha, min_val, max_val = 0.40, 0.5, 1.0
    
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    exp = f"ใช้สูตร: ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมที่ {ce:.3f}"
    if z < 6.0: exp = f"ความสูง {z}ม. < 6.0ม. ให้คิดที่ 6.0ม. | " + exp
    return ce, exp

# ==========================================
# Streamlit UI Setup & Custom CSS
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro V2.0", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 20px; }
    .section-header { font-size: 1.3rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 10px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .card-stat { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer Pro V2.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิรายชั้น, แผนภาพ Tributary Area และเปรียบเทียบแรงเฉือนฐานอาคาร (รองรับหลังคาจั่ว และภูมิประเทศ)</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดการออกแบบ")

st.sidebar.subheader("1. พารามิเตอร์แรงลมและภูมิประเทศ")
prov_choice = st.sidebar.selectbox("ความเร็วลมพื้นที่", list(PROVINCE_V.keys()))
if "Manual" in prov_choice: V_input = st.sidebar.number_input("ความเร็วลม V (m/s)", value=25.0, step=1.0)
else: V_input = PROVINCE_V[prov_choice]
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง/ต้นไม้เยอะ)', 'C (ในเมือง/ตึกสูง)'], index=1)
Ct_input = st.sidebar.number_input("ตัวคูณภูมิประเทศ Ct (เนินเขา/หน้าผา)", value=1.00, step=0.01, help="ค่าปกติ = 1.0, หากอยู่บนหน้าผาหรือเนินเขาให้ระบุ > 1.0 ตาม มยผ.")
Iw_input = st.sidebar.selectbox("ค่าความสำคัญ (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. แรงแผ่นดินไหว (Base Shear)")
eq_mode = st.sidebar.radio("ที่มาของแผ่นดินไหว (V_EQ):", ["โปรแกรมประมาณการ (Equivalent Static)", "ระบุแรงเฉือนฐานเอง (kN)"])
if "ประมาณการ" in eq_mode:
    w_dl_ll = st.sidebar.number_input("น้ำหนักตึกเฉลี่ยรายชั้น (kgf/m²)", value=600.0, step=50.0)
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
else:
    V_EQ_manual = st.sidebar.number_input("ระบุ V_EQ (kN)", value=120.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์ประกอบอาคารและหลังคา")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)

st.sidebar.markdown("**[ ข้อมูลหลังคาอาคาร ]**")
roof_type = st.sidebar.radio("ประเภทหลังคา:", ["แบน (Flat Roof)", "จั่ว / เพิงแหงน (Gable Roof)"])
if "แบน" in roof_type:
    Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Roof Uplift)", value=-0.7, step=0.05)
    roof_angle = 0.0
    h_roof = 0.0
else:
    roof_angle = st.sidebar.number_input("ความชันหลังคา (องศา)", value=15.0, step=1.0)
    Cp_r_w = st.sidebar.number_input("Cp หลังคาฝั่งรับลม (Windward)", value=-0.9, step=0.05)
    Cp_r_l = st.sidebar.number_input("Cp หลังคาฝั่งตามลม (Leeward)", value=-0.5, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: B = st.number_input("ความกว้างอาคารขนานลม B (ม.)", value=15.0, min_value=1.0)
with c2: L = st.number_input("ความยาวอาคารตั้งฉากลม L (ม.)", value=20.0, min_value=1.0)
with c3: num_stories = st.number_input("จำนวนชั้นอาคารทั้งหมด", value=3, min_value=1)

with st.expander("📐 ปรับแต่งความสูงแยกรายชั้น (กรณีตึกแต่ละชั้นสูงไม่เท่ากัน)", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        with floor_cols[i % 4]:
            h_val = st.number_input(f"ชั้น {i+1} (ม.)", value=4.0 if i==0 else 3.5, min_value=1.0, key=f"h_{i}")
            floor_heights.append(h_val)
H_total = sum(floor_heights)

# คำนวณความสูงยอดจั่ว (ถ้ามี)
if "จั่ว" in roof_type:
    h_roof = (B / 2.0) * math.tan(math.radians(roof_angle))

# ==========================================
# ENGINE: ประมวลผลทางวิศวกรรม
# ==========================================
q = calculate_q(V_input)
Ce_H, _ = get_Ce_details(H_total, exposure)
qh = q * Ce_H * Ct_input # ประยุกต์ใช้ตัวคูณผลกระทบภูมิประเทศ Ct

p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_int_pos = qh * GCpi     
p_int_neg = qh * (-GCpi)  

net_l_c1, net_l_c2 = p_leeward - p_int_neg, p_leeward - p_int_pos

# --- การประมวลผลแรงลัพธ์หลังคา ---
if "แบน" in roof_type:
    p_roof = Iw_input * qh * Cg_input * Cp_r
    force_roof_horiz = 0.0 # หลังคาแบนไม่มีพื้นที่ตั้งฉากรับแรงเฉือนแนวราบ
else:
    # หลังคาจั่ว คิดแรงดันฝั่งรับลมและตามลม
    p_roof_w = Iw_input * qh * Cg_input * Cp_r_w
    p_roof_l = Iw_input * qh * Cg_input * Cp_r_l
    
    # คำนวณ Horizontal Shear ของหลังคา (แรงดันสุทธิฝั่งซ้าย - ฝั่งขวา คูณด้วยพื้นที่โปรเจคชั่นแนวดิ่ง)
    # หมายเหตุ: แรงดันภายใน (Internal) หักล้างกันในแนวนอนเสมอ จึงคำนวณจาก external ได้โดยตรง
    area_vert_roof = h_roof * L
    force_roof_horiz = (p_roof_w - p_roof_l) * area_vert_roof * 0.00980665

# --- การประมวลผลแรงรายชั้น ---
z_cum = 0
floors_data = []

for i in range(num_stories):
    h = floor_heights[i]
    z_bot, z_top = z_cum, z_cum + h
    z_mid = (z_bot + z_top) / 2.0
    
    Ce_mid, Ce_exp = get_Ce_details(z_mid, exposure)
    p_w = Iw_input * q * Ce_mid * Ct_input * Cg_input * Cp_w # นำ Ct มาเร่งความเร็วลมรายชั้น
    
    net_w_c1 = p_w - p_int_neg
    net_w_c2 = p_w - p_int_pos
    
    area_front = L * h  
    
    force_w_ext = p_w * area_front * 0.00980665
    force_w_c1 = net_w_c1 * area_front * 0.00980665
    force_w_c2 = net_w_c2 * area_front * 0.00980665
    
    force_l_ext = p_leeward * area_front * 0.00980665
    force_l_c1 = net_l_c1 * area_front * 0.00980665
    force_l_c2 = net_l_c2 * area_front * 0.00980665
    
    force_c1 = force_w_c1 - force_l_c1
    force_c2 = force_w_c2 - force_l_c2
    
    floors_data.append({
        "floor": i+1, "h": h, "z_bot": z_bot, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_exp, "p_w": p_w,
        "net_w_c1": net_w_c1, "net_w_c2": net_w_c2,
        "area_front": area_front,
        "force_w_ext": force_w_ext, "force_w_c1": force_w_c1, "force_w_c2": force_w_c2,
        "force_l_ext": force_l_ext, "force_l_c1": force_l_c1, "force_l_c2": force_l_c2,
        "force_c1": force_c1, "force_c2": force_c2
    })
    z_cum = z_top

V_wind_c1 = sum([f['force_c1'] for f in floors_data]) + force_roof_horiz
V_wind_c2 = sum([f['force_c2'] for f in floors_data]) + force_roof_horiz
V_wind_max = max(V_wind_c1, V_wind_c2)

if "ประมาณการ" in eq_mode:
    W_kN = (B * L) * num_stories * w_dl_ll * 0.00980665
    V_EQ_calc = cs_coeff * W_kN
else:
    V_EQ_calc = V_EQ_manual

# ==========================================
# PLOTLY FUNCTIONS (ระบบกราฟิกแบบ Dynamic ทรงตึก)
# ==========================================
def plot_cross_section(floors, mode, unit_display):
    fig = go.Figure()
    
    # เช็กวาดทรงอาคาร (แบน หรือ จั่ว)
    if "แบน" in roof_type:
        fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"))
    else:
        # วาดพิกัดยอดจั่วเพิ่มที่ x=B/2
        fig.add_trace(go.Scatter(x=[0, B, B, B/2, 0, 0], y=[0, 0, H_total, H_total+h_roof, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"))
        
    is_kn = "kN" in unit_display
    unit_lbl = "kN" if is_kn else "kgf/m²"

    def draw_arrow(x_tail, y_tail, x_head, y_head, val, col, x_anc):
        fig.add_annotation(x=x_head, y=y_head, ax=x_tail, ay=y_tail, xref="x", yref="y", axref="x", ayref="y",
            text=f"<b>{val:.1f} {unit_lbl}</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor=col, font=dict(color=col, size=13), xanchor=x_anc)

    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="gray", width=1.5, dash="dash"))
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}</b>", showarrow=False, font=dict(color="#4B5563", size=12))
        
        if not is_kn:
            val_w = f['p_w'] if mode == "External" else (f['net_w_c1'] if mode == "Case 1" else f['net_w_c2'])
            arr_len = max(2.0, min(3.5, 1.0 + abs(val_w)/30.0))
            if val_w >= 0: draw_arrow(-arr_len, f['z_mid'], 0, f['z_mid'], val_w, "#DC2626", "right")
            else: draw_arrow(0, f['z_mid'], -arr_len, f['z_mid'], val_w, "#9333EA", "left")
        else:
            force_w = f['force_w_ext'] if mode == "External" else (f['force_w_c1'] if mode == "Case 1" else f['force_w_c2'])
            force_l = f['force_l_ext'] if mode == "External" else (f['force_l_c1'] if mode == "Case 1" else f['force_l_c2'])
            net_story_force = force_w - force_l
            arr_len = max(3.0, min(6.0, 2.0 + abs(net_story_force)/40.0))
            draw_arrow(-arr_len, f['z_top'], 0, f['z_top'], net_story_force, "#2563EB", "right")

    # วาด Leeward ของผนัง
    if not is_kn:
        val_l = p_leeward if mode == "External" else (net_l_c1 if mode == "Case 1" else net_l_c2)
        arr_len = max(2.0, min(3.5, 1.0 + abs(val_l)/30.0))
        if val_l >= 0: draw_arrow(B+arr_len, H_total/2, B, H_total/2, val_l, "#DC2626", "left")
        else: draw_arrow(B, H_total/2, B+arr_len, H_total/2, val_l, "#EA580C", "right")
        
        # วาดแรงบนหลังคาตามประเภท
        if "แบน" in roof_type:
            val_r = p_roof if mode == "External" else (p_roof - p_int_neg if mode == "Case 1" else p_roof - p_int_pos)
            if val_r >= 0: draw_arrow(B/2, H_total+2.5, B/2, H_total, val_r, "#DC2626", "center")
            else: draw_arrow(B/2, H_total, B/2, H_total+2.5, val_r, "#9333EA", "center")
        else:
            # หลังคาจั่ว: วาดลูกศรฝั่งรับลมและตามลม (แสดงเป็นแนวดิ่งเพื่อให้กราฟิกดูง่าย)
            val_rw = p_roof_w if mode == "External" else (p_roof_w - p_int_neg if mode == "Case 1" else p_roof_w - p_int_pos)
            val_rl = p_roof_l if mode == "External" else (p_roof_l - p_int_neg if mode == "Case 1" else p_roof_l - p_int_pos)
            draw_arrow(B/4, H_total + h_roof/2 + 2, B/4, H_total + h_roof/2, val_rw, "#DC2626" if val_rw >= 0 else "#9333EA", "center")
            draw_arrow(3*B/4, H_total + h_roof/2 + 2, 3*B/4, H_total + h_roof/2, val_rl, "#EA580C" if val_rl >= 0 else "#9333EA", "center")
            
    else: # โหมด kN
        if "จั่ว" in roof_type:
            # วาดลูกศร Point Load แนวนอนของยอดหลังคา
            arr_len = max(3.0, min(6.0, 2.0 + abs(force_roof_horiz)/40.0))
            draw_arrow(-arr_len, H_total + h_roof/2, 0, H_total + h_roof/2, force_roof_horiz, "#2563EB", "right")

    fig.update_layout(title=f"<b>1. แผนภาพหน้าตัด (Cross Section) - โหมด {mode} ({unit_lbl})</b>", 
                      xaxis_title="ความกว้างอาคาร B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)", 
                      xaxis_range=[-9, B+9], yaxis_range=[-1, H_total + h_roof + 5], height=550, plot_bgcolor="white", margin=dict(t=40,b=20))
    fig.update_xaxes(showgrid=True, gridcolor='#F3F4F6'); fig.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
    return fig

# ==========================================
# INTERACTIVE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แผนภาพจำลองแรงลม (Visualizations)", "⚖️ วิเคราะห์แรงเฉือนฐาน (Base Shear)", "📑 เล่มรายการคำนวณและตาราง (Calculation)"])

with tab1:
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="card-stat"><p>ความสูงตึกอ้างอิง</p><h3>{H_total:.2f} ม.</h3></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="card-stat"><p>ตัวคูณภูมิประเทศ (Ct)</p><h3>{Ct_input:.2f}</h3></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="card-stat"><p>Net Windward สูงสุด</p><h3 style="color:#DC2626;">{max([f["net_w_c1"] for f in floors_data]):.1f} kgf/m²</h3></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="card-stat"><p>แรงลมรวมฐาน (V_Wind)</p><h3 style="color:#2563EB;">{V_wind_max:.2f} kN</h3></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    c_opt1, c_opt2 = st.columns([3, 2])
    with c_opt1:
        view_opt = st.radio("🔘 **เลือกกรณีโหลด (Load Case):**", ["External", "Case 1", "Case 2"], horizontal=True)
    with c_opt2:
        unit_opt = st.radio("📐 **เลือกหน่วยแสดงผลบนกราฟิก:**", ["kgf/m² (หน่วยแรงกระจาย)", "kN (แรงลัพธ์แบบจุด Point Load)"], horizontal=True)
    
    st.plotly_chart(plot_cross_section(floors_data, view_opt, unit_opt), use_container_width=True)

with tab2:
    st.markdown("#### ⚖️ การตรวจสอบและเปรียบเทียบแรงเฉือนที่ฐานอาคาร (Base Shear Comparison)")
    gov_force = "🌪️ WIND LOAD (แรงลมควบคุมการออกแบบ)" if V_wind_max > V_EQ_calc else "🚨 EARTHQUAKE LOAD (แรงแผ่นดินไหวควบคุม)"
    c_box = "#FEE2E2" if V_wind_max > V_EQ_calc else "#E0F2FE"
    c_border = "#EF4444" if V_wind_max > V_EQ_calc else "#0284C7"
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=["แรงลม Case 1", "แรงลม Case 2", "แรงแผ่นดินไหว (V_EQ)"], y=[V_wind_c1, V_wind_c2, V_EQ_calc],
                             marker_color=["#3B82F6", "#1D4ED8", "#EF4444"], text=[f"{V_wind_c1:.1f} kN", f"{V_wind_c2:.1f} kN", f"{V_EQ_calc:.1f} kN"], textposition='auto'))
    fig_bar.update_layout(title="<b>เปรียบเทียบแรงเฉือนฐานราก (Base Shear: kN)</b>", yaxis_title="kN", height=400, plot_bgcolor="white")
    
    b1, b2 = st.columns([3, 2])
    with b1: st.plotly_chart(fig_bar, use_container_width=True)
    with b2:
        st.markdown(f'<div class="verdict-box" style="background-color:{c_box}; border-left:6px solid {c_border};">{gov_force}</div>', unsafe_allow_html=True)
        st.markdown(f"* **แรงลมสูงสุด ($V_{{Wind}}$):** `{V_wind_max:.2f}` kN\n* **แผ่นดินไหว ($V_{{EQ}}$):** `{V_EQ_calc:.2f}` kN\n* อัตราส่วน $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / max(V_EQ_calc, 1):.2f}`** เท่า")

# --- TAB 3: Calculation Report ---
with tab3:
    st.title("📑 รายการคำนวณแรงลมสุทธิโดยละเอียด (Meticulous Wind Load Report)")
    st.markdown("---")
    st.subheader("1. ข้อมูลรูปทรงอาคารและพารามิเตอร์การออกแบบหลัก")
    c_inf1, c_inf2, c_inf3 = st.columns(3)
    with c_inf1:
        st.markdown(f"**ความเร็วลมออกแบบ (V):** `{V_input}` m/s")
        st.markdown(f"**ตัวคูณภูมิประเทศ (Ct):** `{Ct_input:.2f}`")
    with c_inf2:
        st.markdown(f"**ความกว้างอาคาร (B):** `{B}` เมตร")
        st.markdown(f"**ความยาวอาคาร (L):** `{L}` เมตร")
    with c_inf3:
        st.markdown(f"**ลักษณะหลังคา:** `{roof_type}`")
        st.markdown(f"**ความสูงยอดอาคารรวม:** `{H_total + h_roof:.2f}` เมตร")

    st.markdown("<div style='border-top: 1px dashed #ddd; margin: 15px 0;'></div>", unsafe_allow_html=True)
    st.markdown("**การคำนวณหน่วยแรงลมปะทะอ้างอิงพื้นฐาน ($q$):**")
    st.latex(r"q = \frac{0.5 \cdot 1.25 \cdot V^2}{9.80665}")
    st.markdown(f"👉 $q = \\mathbf{{{q:.3f}\\text{{ kgf/m}}^2}}$")

    st.subheader("2. ขั้นตอนการแทนค่าสูตรคำนวณจำแนกตามช่วงชั้นความสูง")
    for idx, f in enumerate(floors_data):
        z_bottom = f['z_bot']
        h_floor = f['h']
        area_floor = f['area_front']
        q_z_mid = q * f['Ce'] * Ct_input
        
        if view_opt == "External": p_w_val = f['p_w']; p_l_val = p_leeward; f_w_val = f['force_w_ext']; f_l_val = f['force_l_ext']; p_int_val = 0.0
        elif view_opt == "Case 1": p_w_val = f['net_w_c1']; p_l_val = net_l_c1; f_w_val = f['force_w_c1']; f_l_val = f['force_l_c1']; p_int_val = p_int_neg
        else: p_w_val = f['net_w_c2']; p_l_val = net_l_c2; f_w_val = f['force_w_c2']; f_l_val = f['force_l_c2']; p_int_val = p_int_pos
            
        net_f_story = f_w_val - f_l_val

        with st.expander(f"🔹 ชั้น {f['floor']} | ช่วงพิกัดความสูง z = {z_bottom:.2f} ถึง {f['z_top']:.2f} ม."):
            st.markdown(f"• **พื้นที่รับลมหน้าตรง ($A_{{front}}$):** {L} ม. × {h_floor:.2f} ม. = **`{area_floor:.2f}` $m^2$**")
            st.markdown(f"• **หน่วยแรงลมอ้างอิง ($q_z$):** $q_z = q \\times C_e \\times C_t = {q:.2f} \\times {f['Ce']:.3f} \\times {Ct_input:.2f} = \\mathbf{{{q_z_mid:.2f}\\text{{ kgf/m}}^2}}$")
            st.markdown(f"• **แรง Windward ($F_w$):** $({p_w_val:.2f}) \\times {area_floor:.2f} \\times 0.00980665 = \\mathbf{{{f_w_val:.2f}\\text{{ kN}}}}$")
            st.markdown(f"• **แรง Leeward ($F_l$):** $({p_l_val:.2f}) \\times {area_floor:.2f} \\times 0.00980665 = \\mathbf{{{f_l_val:.2f}\\text{{ kN}}}}$")
            st.success(f"🎯 **สรุปแรงเข้า Diaphragm ชั้น {f['floor']}:** เกิดแรงปะทะด้านข้างรวม **{net_f_story:.2f} kN** กระทำที่พิกัด **z = {f['z_top']:.2f} ม.**")

    # พิเศษสำหรับหลังคาจั่ว
    if "จั่ว" in roof_type:
        with st.expander(f"🔺 แรงเฉือนแนวราบจากหลังคาจั่ว (Roof Horizontal Shear) | ความชัน {roof_angle} องศา"):
            st.markdown(f"• พื้นที่โปรเจคชั่นแนวดิ่งของหลังคา: $h_{{roof}} \\times L = {h_roof:.2f} \\times {L} = \\mathbf{{{area_vert_roof:.2f}\\text{{ m}}^2}}$")
            st.markdown(f"• แรงดันฝั่งรับลม ($p_{{r,w}}$): **`{p_roof_w:.2f}`** kgf/m² | ฝั่งตามลม ($p_{{r,l}}$): **`{p_roof_l:.2f}`** kgf/m²")
            st.markdown(f"• แรงเฉือนแนวนอน: $F_{{roof}} = (p_{{r,w}} - p_{{r,l}}) \\times A_{{vert}} \\times 0.00980665$")
            st.success(f"🎯 **สรุปแรงเข้าคานรัดหัวเสา:** เกิดแรงเฉือนเสริมจากหลังคา **{force_roof_horiz:.2f} kN**")

    st.write("---")
    st.subheader("3. การคำนวณแรงเฉือนที่ฐานอาคารรวม (Total Base Shear Calculation)")
    
    current_case_forces = [ (f['force_w_ext'] - f['force_l_ext']) if view_opt == "External" else ((f['force_w_c1'] - f['force_l_c1']) if view_opt == "Case 1" else (f['force_w_c2'] - f['force_l_c2'])) for f in floors_data ]
    
    force_strings = [f"{force:.2f}" for force in current_case_forces]
    if "จั่ว" in roof_type:
        force_strings.append(f"{force_roof_horiz:.2f} (Roof)")
        total_base_shear_current = sum(current_case_forces) + force_roof_horiz
    else:
        total_base_shear_current = sum(current_case_forces)

    equation_str = " + ".join(force_strings)
    st.markdown(f"👉 **แทนค่าจากตาราง (กรณี {view_opt}):** $V_{{wind}} = {equation_str}$")
    st.markdown(f"👉 **ผลลัพธ์แรงเฉือนฐานรวม:** $V_{{wind}} = \\mathbf{{{total_base_shear_current:.2f}\\text{{ kN}}}}$")
