import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
    exp = f"ใช้สูตร: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมที่ {ce:.3f}"
    if z < 6.0: exp = f"ความสูง {z}ม. < 6.0ม. ให้คิดที่ 6.0ม. | " + exp
    return ce, exp

# ==========================================
# Streamlit UI Setup & Custom CSS
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 20px; }
    .section-header { font-size: 1.3rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 10px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .card-stat { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิรายชั้น, แผนภาพ Tributary Area และเปรียบเทียบแรงเฉือนฐานอาคาร (มยผ. 1311-50 / 1302)</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดการออกแบบ")

st.sidebar.subheader("1. พารามิเตอร์แรงลม")
prov_choice = st.sidebar.selectbox("ความเร็วลมพื้นที่", list(PROVINCE_V.keys()))
if "Manual" in prov_choice: V_input = st.sidebar.number_input("ความเร็วลม V (m/s)", value=25.0, step=1.0)
else: V_input = PROVINCE_V[prov_choice]
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง/ต้นไม้เยอะ)', 'C (ในเมือง/ตึกสูง)'], index=1)
Iw_input = st.sidebar.selectbox("ค่าความสำคัญ (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 2. แรงแผ่นดินไหว (Base Shear)")
eq_mode = st.sidebar.radio("ที่มาของแผ่นดินไหว (V_EQ):", ["โปรแกรมประมาณการ (Equivalent Static)", "ระบุแรงเฉือนฐานเอง (kN)"])
if "ประมาณการ" in eq_mode:
    w_dl_ll = st.sidebar.number_input("น้ำหนักตึกรวมเฉลี่ยรายชั้น (kgf/m²)", value=600.0, step=50.0)
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
else:
    V_EQ_manual = st.sidebar.number_input("ระบุ V_EQ (kN)", value=120.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("3. สัมประสิทธิ์ประกอบอาคาร")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially)"])
Cg_input = st.sidebar.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
Cp_w = st.sidebar.number_input("Cp ด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ด้านตามลม (Leeward)", value=-0.5, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Roof Uplift)", value=-0.7, step=0.05)
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

# ==========================================
# ENGINE: ประมวลผลทางวิศวกรรม
# ==========================================
q = calculate_q(V_input)
Ce_H, _ = get_Ce_details(H_total, exposure)
qh = q * Ce_H

# โหลดแรงดันแผ่คงที่ (kgf/m²)
p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_roof = Iw_input * qh * Cg_input * Cp_r
p_int_pos = qh * GCpi     
p_int_neg = qh * (-GCpi)  

# Net แรงดันแผ่คงที่ (kgf/m²)
net_l_c1, net_l_c2 = p_leeward - p_int_neg, p_leeward - p_int_pos
net_r_c1, net_r_c2 = p_roof - p_int_neg, p_roof - p_int_pos

# โหลดแรงลัพธ์ (kN) บริเวณหลังคา
area_roof = B * L
force_r_ext = p_roof * area_roof * 0.00980665
force_r_c1 = net_r_c1 * area_roof * 0.00980665
force_r_c2 = net_r_c2 * area_roof * 0.00980665

z_cum = 0
floors_data = []

for i in range(num_stories):
    h = floor_heights[i]
    z_bot, z_top = z_cum, z_cum + h
    z_mid = (z_bot + z_top) / 2.0
    
    Ce_mid, Ce_exp = get_Ce_details(z_mid, exposure)
    p_w = Iw_input * q * Ce_mid * Cg_input * Cp_w
    
    net_w_c1 = p_w - p_int_neg
    net_w_c2 = p_w - p_int_pos
    
    area_front = L * h  # พื้นที่รับลมหลัก (หน้าตรง)
    
    # คำนวณ Point Load (kN) ของฝั่ง Windward และ Leeward แยกรายชั้น!
    force_w_ext = p_w * area_front * 0.00980665
    force_w_c1 = net_w_c1 * area_front * 0.00980665
    force_w_c2 = net_w_c2 * area_front * 0.00980665
    
    force_l_ext = p_leeward * area_front * 0.00980665
    force_l_c1 = net_l_c1 * area_front * 0.00980665
    force_l_c2 = net_l_c2 * area_front * 0.00980665
    
    # Story Force สุทธิ (kN) = Force_Windward - Force_Leeward
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

V_wind_c1 = sum([f['force_c1'] for f in floors_data])
V_wind_c2 = sum([f['force_c2'] for f in floors_data])
V_wind_max = max(V_wind_c1, V_wind_c2)

if "ประมาณการ" in eq_mode:
    W_kN = (B * L) * num_stories * w_dl_ll * 0.00980665
    V_EQ_calc = cs_coeff * W_kN
else:
    V_EQ_calc = V_EQ_manual

# ==========================================
# PLOTLY FUNCTIONS (ระบบลูกศรอัจฉริยะ)
# ==========================================

def plot_cross_section(floors, mode, unit_display):
    fig = go.Figure()
    # วาดรูปหน้าตัดอาคาร
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"))
    
    is_kn = "kN" in unit_display
    unit_lbl = "kN" if is_kn else "kgf/m²"

    # ฟังก์ชันวาดย่อยที่ควบคุมพิกัด หัว-หาง ของลูกศร
    def draw_arrow(x_tail, y_tail, x_head, y_head, val, col, x_anc):
        fig.add_annotation(
            x=x_head, y=y_head, ax=x_tail, ay=y_tail,
            xref="x", yref="y", axref="x", ayref="y",
            text=f"<b>{val:.1f} {unit_lbl}</b>",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor=col,
            font=dict(color=col, size=13), xanchor=x_anc
        )

    for f in floors:
        # วาดเส้นประแสดงระดับพื้น (Floor Line) ของแต่ละชั้น
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="gray", width=1.5, dash="dash"))
        
        # ใส่ข้อความชื่อชั้นไว้กึ่งกลางช่วงความสูงเสมอเพื่อความเช็คสถานะง่าย
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}</b>", showarrow=False, font=dict(color="#4B5563", size=12))
        
        if not is_kn:
            # 1. โหมด kgf/m²: วาดแรงดันลมแผ่กระจาย เข้าที่กึ่งกลางความสูงผนัง (z_mid) ของชั้นนั้นๆ
            val_w = f['p_w'] if mode == "External" else (f['net_w_c1'] if mode == "Case 1" else f['net_w_c2'])
            arr_len = max(2.0, min(3.5, 1.0 + abs(val_w)/30.0))
            if val_w >= 0: draw_arrow(-arr_len, f['z_mid'], 0, f['z_mid'], val_w, "#DC2626", "right")
            else: draw_arrow(0, f['z_mid'], -arr_len, f['z_mid'], val_w, "#9333EA", "left")
        else:
            # 2. โหมด kN: วาด Point Load ลัพธ์ประจำชั้น วิ่งเข้าที่ "ระดับแผ่นพื้น" (z_top) ของชั้นนั้นๆ พอดีเป๊ะ!
            force_w = f['force_w_ext'] if mode == "External" else (f['force_w_c1'] if mode == "Case 1" else f['force_w_c2'])
            force_l = f['force_l_ext'] if mode == "External" else (f['force_l_c1'] if mode == "Case 1" else f['force_l_c2'])
            net_story_force = force_w - force_l
            
            arr_len = max(3.0, min(6.0, 2.0 + abs(net_story_force)/40.0))
            # หัวลูกศรจะจิ้มเข้าที่ x=0 (ฝั่งรับลม) และระดับความสูง z_top ของชั้นนั้นๆ (ตรงแนวเส้นประพอดี)
            draw_arrow(-arr_len, f['z_top'], 0, f['z_top'], net_story_force, "#2563EB", "right")

    # วาดแรงฝั่ง Leeward และ Roof
    if not is_kn:
        # โหมด kgf/m²: Leeward เป็นแรงกระจายคงที่ แสดงไว้ตรงกลางความสูงอาคารรวม
        val_l = p_leeward if mode == "External" else (net_l_c1 if mode == "Case 1" else net_l_c2)
        arr_len = max(2.0, min(3.5, 1.0 + abs(val_l)/30.0))
        if val_l >= 0: draw_arrow(B+arr_len, H_total/2, B, H_total/2, val_l, "#DC2626", "left")
        else: draw_arrow(B, H_total/2, B+arr_len, H_total/2, val_l, "#EA580C", "right")
        
        # วาดแรงดันหลังคา
        val_r = p_roof if mode == "External" else (net_r_c1 if mode == "Case 1" else net_r_c2)
        arr_len_r = max(2.0, min(3.5, 1.0 + abs(val_r)/30.0))
        if val_r >= 0: draw_arrow(B/2, H_total+arr_len_r, B/2, H_total, val_r, "#DC2626", "center")
        else: draw_arrow(B/2, H_total, B/2, H_total+arr_len_r, val_r, "#9333EA", "center")
    else:
        # โหมด kN: วาดแรงลัพธ์ดึงขึ้นของหลังคา (Roof Point Load) กระทำตรงกลางแนวหลังคา (H_total)
        val_r = force_r_ext if mode == "External" else (force_r_c1 if mode == "Case 1" else force_r_c2)
        arr_len_r = max(2.5, min(5.0, 1.5 + abs(val_r)/50.0))
        if val_r >= 0: draw_arrow(B/2, H_total+arr_len_r, B/2, H_total, val_r, "#DC2626", "center")
        else: draw_arrow(B/2, H_total, B/2, H_total+arr_len_r, val_r, "#9333EA", "center")

    # ขยาย Range เผื่อระยะลูกศร เพื่อป้องกันกราฟบีบตัวจนสเกลเพี้ยน
    fig.update_layout(title=f"<b>1. แผนภาพหน้าตัด (Cross Section) - โหมด {mode} ({unit_lbl})</b>", 
                      xaxis_title="ความกว้างอาคาร B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)", 
                      xaxis_range=[-9, B+9], yaxis_range=[-1, H_total+5], height=550, plot_bgcolor="white", margin=dict(t=40,b=20))
    fig.update_xaxes(showgrid=True, gridcolor='#F3F4F6'); fig.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
    return fig

def plot_elevation(floors, length_dim, label):
    fig = go.Figure()
    colors = ["#93C5FD", "#60A5FA", "#3B82F6", "#2563EB"]
    for idx, f in enumerate(floors):
        area = f['area_front'] 
        fig.add_trace(go.Scatter(x=[0, length_dim, length_dim, 0, 0], y=[f['z_bot'], f['z_bot'], f['z_top'], f['z_top'], f['z_bot']],
            fill="toself", fillcolor=colors[idx % 4], line=dict(color="#1E3A8A", width=1.5), showlegend=False))
        fig.add_annotation(x=length_dim/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}: Area = {area:.1f} m²</b><br>(กว้าง {length_dim}ม. × สูงช่วงชั้น {f['h']}ม.)", showarrow=False, font=dict(color="white", size=14))
    
    fig.update_layout(title=f"<b>2. ขอบเขตพื้นที่รับลมหน้าตรง Tributary Area ({label})</b>", xaxis_title="ความยาวหน้าแผง L (ม.)", yaxis_title="ความสูง (ม.)", height=550, plot_bgcolor="white", margin=dict(t=40,b=20))
    return fig

# ==========================================
# INTERACTIVE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แผนภาพจำลองแรงลม (Visualizations)", "⚖️ วิเคราะห์แรงเฉือนฐาน (Base Shear)", "📑 เล่มรายการคำนวณและตาราง (Calculation)"])

# --- TAB 1: Visualizations (บน-ล่าง ขยายเต็มจอ) ---
with tab1:
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="card-stat"><p>ความสูงตึก (H)</p><h3>{H_total:.2f} ม.</h3></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="card-stat"><p>แรงลมอ้างอิง (q)</p><h3>{q:.2f} kgf/m²</h3></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="card-stat"><p>Net Windward สูงสุด</p><h3 style="color:#DC2626;">{max([f["net_w_c1"] for f in floors_data]):.1f} kgf/m²</h3></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="card-stat"><p>แรงลมรวมฐาน (V_Wind)</p><h3 style="color:#2563EB;">{V_wind_max:.2f} kN</h3></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    c_opt1, c_opt2 = st.columns([3, 2])
    with c_opt1:
        view_opt = st.radio("🔘 **เลือกกรณีโหลด (Load Case):**", 
                            ["External", "Case 1", "Case 2"], 
                            captions=["แรงลมภายนอก 100%", "สุทธิ Case 1: ผสมแรงดูดภายใน (-)", "สุทธิ Case 2: ผสมแรงดันภายใน (+)"], horizontal=True)
    with c_opt2:
        unit_opt = st.radio("📐 **เลือกหน่วยแสดงผลบนกราฟิก:**", 
                            ["kgf/m² (หน่วยแรงกระจาย)", "kN (แรงลัพธ์แบบจุด Point Load)"], horizontal=True)
    
    st.plotly_chart(plot_cross_section(floors_data, view_opt, unit_opt), use_container_width=True)
    st.markdown("---")
    st.plotly_chart(plot_elevation(floors_data, L, "Front View - ด้านตั้งฉากลม L"), use_container_width=True)

# --- TAB 2: Base Shear Analyzer ---
with tab2:
    st.markdown("#### ⚖️ การตรวจสอบและเปรียบเทียบแรงเฉือนที่ฐานอาคาร (Base Shear Comparison)")
    
    gov_force = "🌪️ WIND LOAD (แรงลมควบคุมการออกแบบ)" if V_wind_max > V_EQ_calc else "🚨 EARTHQUAKE LOAD (แรงแผ่นดินไหวควบคุม)"
    c_box = "#FEE2E2" if V_wind_max > V_EQ_calc else "#E0F2FE"
    c_border = "#EF4444" if V_wind_max > V_EQ_calc else "#0284C7"
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=["แรงลม Case 1", "แรงลม Case 2", "แรงแผ่นดินไหว (V_EQ)"],
        y=[V_wind_c1, V_wind_c2, V_EQ_calc],
        marker_color=["#3B82F6", "#1D4ED8", "#EF4444"],
        text=[f"{V_wind_c1:.1f} kN", f"{V_wind_c2:.1f} kN", f"{V_EQ_calc:.1f} kN"], textposition='auto'
    ))
    fig_bar.update_layout(title="<b>เปรียบเทียบแรงเฉือนฐานราก (Base Shear: kN)</b>", yaxis_title="kN", height=400, plot_bgcolor="white")
    
    b1, b2 = st.columns([3, 2])
    with b1: st.plotly_chart(fig_bar, use_container_width=True)
    with b2:
        st.markdown(f'<div class="verdict-box" style="background-color:{c_box}; border-left:6px solid {c_border};">{gov_force}</div>', unsafe_allow_html=True)
        st.markdown(f"""
        * **แรงลมสูงสุด ($V_{{Wind}}$):** `{V_wind_max:.2f}` kN
        * **แผ่นดินไหว ($V_{{EQ}}$):** `{V_EQ_calc:.2f}` kN
        * อัตราส่วน $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / max(V_EQ_calc, 1):.2f}`** เท่า
        """)

# --- TAB 3: Calculation & Export (เวอร์ชันละเอียดสูงสุดเพื่อส่งตรวจราชการ/Checker) ---
with tab3:
    st.title("📑 รายการคำนวณแรงลมสุทธิโดยละเอียด (Meticulous Wind Load Report)")
    st.caption("อ้างอิงมาตรฐาน มยผ. 1311-50 / 1302 มาตรฐานการคำนวณแรงลมและการตอบสนองของโครงสร้าง")
    st.markdown("---")
    
    # ----------------------------------------------------
    # SECTION 1: ข้อมูลและพารามิเตอร์ตั้งต้นของโครงการ
    # ----------------------------------------------------
    st.subheader("1. ข้อมูลรูปทรงอาคารและพารามิเตอร์การออกแบบหลัก")
    
    c_inf1, c_inf2, c_inf3 = st.columns(3)
    with c_inf1:
        st.markdown(f"**ความเร็วลมออกแบบ (V):** `{V_input}` m/s")
        st.markdown(f"**สภาพภูมิประเทศ (Exposure):** `{exposure}`")
        st.markdown(f"**ค่าน้ำหนักความสำคัญ (Iw):** `{Iw_input}`")
    with c_inf2:
        st.markdown(f"**ความกว้างอาคารขนานลม (B):** `{B}` เมตร")
        st.markdown(f"**ความยาวอาคารตั้งฉากลม (L):** `{L}` เมตร")
        st.markdown(f"**ความสูงรวมอาคาร (H):** `{H_total:.2f}` เมตร")
    with c_inf3:
        st.markdown(f"**ลักษณะการปิดล้อม:** `{enclosure}`")
        st.markdown(f"**ประกอบลมกระโชก (Cg):** `{Cg_input}`")
        st.markdown(f"**จำนวนชั้นทั้งหมด:** `{num_stories}` ชั้น")

    st.markdown("<div style='border-top: 1px dashed #ddd; margin: 15px 0;'></div>", unsafe_allow_html=True)
    
    # แสดงการคำนวณค่าคงที่หลักของอาคาร
    st.markdown("**การคำนวณหน่วยแรงลมปะทะอ้างอิงพื้นฐาน (Reference Velocity Pressure, $q$):**")
    st.latex(r"q = \frac{0.5 \cdot \rho \cdot V^2}{g} = \frac{0.5 \cdot 1.25 \cdot V^2}{9.80665}")
    st.markdown(f"👉 **แทนค่า:** $q = \\frac{{0.5 \\times 1.25 \\times {V_input}^2}}{{9.80665}} = \\mathbf{{{q:.3f}\\text{{ kgf/m}}^2}}$")
    
    st.markdown("**การคำนวณแรงดันภายในอาคาร (Internal Pressure, $p_{{internal}}$):**")
    st.latex(r"p_{internal} = q_h \cdot (\pm GC_{pi}) \quad [q_h = q \cdot C_{e,H} = " + f"{q:.2f} \\times {Ce_H:.3f} = {qh:.2f}\\text{{ kgf/m}}^2]")
    st.markdown(f"• กรณีแรงลมดูดภายใน (Internal Suction: คาสัญญาณลบ): $p_{{int,-}} = {qh:.2f} \\times (-{GCpi}) = \\mathbf{{{p_int_neg:.2f}\\text{{ kgf/m}}^2}}$")
    st.markdown(f"• กรณีแรงดันพุ่งออกภายใน (Internal Pressure: คาสัญญาณบวก): $p_{{int,+}} = {qh:.2f} \\times {GCpi} = \\mathbf{{{p_int_pos:.2f}\\text{{ kgf/m}}^2}}$")

    # ----------------------------------------------------
    # SECTION 2: สมการควบคุมทางวิศวกรรม
    # ----------------------------------------------------
    st.subheader("2. ระเบียบวิธีและสมการควบคุมกลศาสตร์โครงสร้าง")
    st.markdown("""
    หน่วยแรงดันลมสุทธิบนผิวอาคาร ($p$) และแรงลัพธ์ประจำชั้น ($F_{net}$) จะคำนวณแยกตามฝั่งรับลม (Windward) 
    และฝั่งท้ายลม (Leeward) โดยดึงค่าสถานะปัจจุบันคือ **Case: %s** ในหน่วย **%s** มาคำนวณสอดคล้องกันดังนี้:
    """ % (view_opt, unit_opt))
    
    st.latex(r"p_{windward} = (I_w \cdot q_z \cdot C_g \cdot C_{p,w}) - p_{internal}")
    st.latex(r"p_{leeward} = (I_w \cdot q_h \cdot C_g \cdot C_{p,l}) - p_{internal}")
    st.latex(r"F_{net} = (p_{windward} \cdot A_{front}) - (p_{leeward} \cdot A_{front})")

    st.markdown("---")

    # ----------------------------------------------------
    # SECTION 3: แจกแจงการคำนวณและแทนค่ารายชั้นอย่างละเอียด
    # ----------------------------------------------------
    st.subheader("3. ขั้นตอนการแทนค่าสูตรคำนวณจำแนกตามช่วงชั้นความสูง")
    st.markdown("*วิศวกรสามารถคลิกเปิดแถบแต่ละชั้นเพื่อตรวจสอบสเต็ปตัวเลขและการแปลงหน่วย $kgf \rightarrow kN$ ได้อย่างละเอียด:*")

    for idx, f in enumerate(floors_data):
        z_bottom = f['z_bot']
        h_floor = f['h']
        area_floor = f['area_front']
        
        # คำนวณค่า q_z ณ ความสูงกึ่งกลางชั้นนั้นๆ
        q_z_mid = q * f['Ce']
        
        # คัดกรองตัวแปรตามโหลดเคสที่วิศวกรเลือกดูบน UI ปัจจุบัน เพื่อแทนค่าตัวเลขให้ตรงเป้า
        if view_opt == "External":
            p_w_val = f['p_w']; p_l_val = p_leeward
            f_w_val = f['force_w_ext']; f_l_val = f['force_l_ext']
            case_desc = "พิจารณาเฉพาะแรงดันผิวภายนอก (External Pressure Only: ไม่คิดแรงดันภายใน)"
            p_int_val = 0.0
        elif view_opt == "Case 1":
            p_w_val = f['net_w_c1']; p_l_val = net_l_c1
            f_w_val = f['force_w_c1']; f_l_val = f['force_l_c1']
            case_desc = f"ผสมแรงดูดภายในอาคารสุทธิ Case 1 ($p_{{internal}} = {p_int_neg:.2f}$ kgf/m²)"
            p_int_val = p_int_neg
        else:
            p_w_val = f['net_w_c2']; p_l_val = net_l_c2
            f_w_val = f['force_w_c2']; f_l_val = f['force_l_c2']
            case_desc = f"ผสมแรงดันภายในอาคารสุทธิ Case 2 ($p_{{internal}} = {p_int_pos:.2f}$ kgf/m²)"
            p_int_val = p_int_pos
            
        net_f_story = f_w_val - f_l_val  # Point Load สุทธิประจำชั้น (kN)

        with st.expander(f"🔹 ชั้น {f['floor']} | ช่วงพิกัดความสูง z = {z_bottom:.2f} ถึง {f['z_top']:.2f} ม. (สถานะ: {view_opt})"):
            
            # ย่อยที่ 1: พิกัดทางกายภาพ
            st.markdown("#### **[สเต็ปที่ A]: ข้อมูลทางกายภาพและพื้นที่รับลม (Tributary Area)**")
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                st.markdown(f"• ระดับความสูงขอบบนพื้นพื้นผิว ($z_{{top}}$): `{f['z_top']:.2f}` ม.")
                st.markdown(f"• ความสูงช่วงชั้นวิเคราะห์ ($h$): `{h_floor:.2f}` ม.")
            with col_a2:
                st.markdown(f"• ระดับกึ่งกลางผนังรับแรงรับลม ($z_{{mid}}$): `{f['z_mid']:.2f}` ม.")
                st.markdown(f"• พื้นที่รับลมหน้าตรงสัมบูรณ์ ($A_{{front}} = L \\times h$): {L} ม. × {h_floor:.2f} ม. = **`{area_floor:.2f}` $m^2$**")
                
            st.markdown("<div style='border-top: 1px dashed #eee; margin: 10px 0;'></div>", unsafe_allow_html=True)
            
            # ย่อยที่ 2: การหา Ce และ qz
            st.markdown("#### **[สเต็ปที่ B]: การหาค่าสัมประสิทธิ์ประกอบภูมิประเทศ ($C_e$) และแรงลมปะทะ ($q_z$)**")
            st.markdown(f"• **การคำนวณค่า $C_e$ ตามข้อกำหนดความสูงสะสม:**")
            st.info(f"🔍 {f['Ce_exp']}")
            st.markdown(f"• **คำนวณหน่วยแรงลมอ้างอิงรายชั้น ($q_z$):**")
            st.latex(r"q_z = q \cdot C_e")
            st.markdown(f"👉 **แทนค่า:** $q_z = {q:.2f} \\times {f['Ce']:.3f} = \\mathbf{{{q_z_mid:.2f}\\text{{ kgf/m}}^2}}$")

            st.markdown("<div style='border-top: 1px dashed #eee; margin: 10px 0;'></div>", unsafe_allow_html=True)

            # ย่อยที่ 3: การคำนวณหาหน่วยแรงดันผิวอาคาร p ทั้งสองฝั่ง
            st.markdown(f"#### **[สเต็ปที่ C]: คำนวณหน่วยแรงดันลมสุทธิที่ผิวอาคาร (Net Pressure, $p$)**")
            st.caption(f"💡 โหมดปัจจุบัน: {case_desc}")
            
            st.markdown("**1. หน่วยแรงดันฝั่งรับลม (Windward Net Pressure, $p_{{windward}}$):**")
            st.latex(r"p_{w} = (I_w \cdot q_z \cdot C_g \cdot C_{p,w}) - p_{internal}")
            # แสดงค่าภายนอกก่อนหักลบภายในให้เห็นภาพชัดๆ
            p_w_ext_only = Iw_input * q_z_mid * Cg_input * Cp_w
            st.markdown(f"👉 **แทนค่า:** $p_{{w}} = ({Iw_input} \\times {q_z_mid:.2f} \\times {Cg_input} \\times {Cp_w}) - ({p_int_val:.2f}) = {p_w_ext_only:.2f} - ({p_int_val:.2f})$")
            st.markdown(f"👉 **ผลลัพธ์แรงดันผิว Windward:** $p_{{windward}} = \\mathbf{{{p_w_val:.2f}\\text{{ kgf/m}}^2}}$")
            
            st.markdown("**2. หน่วยแรงดันฝั่งท้ายลม (Leeward Net Pressure, $p_{{leeward}}$):**")
            st.latex(r"p_{l} = (I_w \cdot q_h \cdot C_g \cdot C_{p,l}) - p_{internal}")
            p_l_ext_only = Iw_input * qh * Cg_input * Cp_l
            st.markdown(f"👉 **แทนค่า:** $p_{{l}} = ({Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times {Cp_l}) - ({p_int_val:.2f}) = {p_l_ext_only:.2f} - ({p_int_val:.2f})$")
            st.markdown(f"👉 **ผลลัพธ์แรงดันผิว Leeward:** $p_{{leeward}} = \\mathbf{{{p_l_val:.2f}\\text{{ kgf/m}}^2}}$ *(เครื่องหมายลบแสดงทิศทางลมดูดออกนอกตึก)*")

            st.markdown("<div style='border-top: 1px dashed #eee; margin: 10px 0;'></div>", unsafe_allow_html=True)

            # ย่อยที่ 4: การคำนวณแรงลัพธ์ประจำชั้น Point Load (kN)
            st.markdown("#### **[สเต็ปที่ D]: การแปลงหน่วยแรงดันแผ่เป็นแรงลัพธ์แบบจุดเข้าสู่แผ่นพื้น (Net Story Load)**")
            st.markdown("ตัวคูณแปลงหน่วยระบบมาตรวัดกลศาสตร์: $1 \\text{{ kgf}} = 9.80665 \\text{{ N}} \\rightarrow 1 \\text{{ kgf}} = 0.00980665 \\text{{ kN}}$")
            
            st.latex(r"F_{windward} = p_{windward} \cdot A_{front} \cdot 0.00980665")
            st.markdown(f"👉 **แทนค่า:** $F_{{w}} = {p_w_val:.2f} \\times {area_floor:.2f} \\times 0.00980665 = \\mathbf{{{f_w_val:.2f}\\text{{ kN}}}}$")
            
            st.latex(r"F_{leeward} = p_{leeward} \cdot A_{front} \cdot 0.00980665")
            st.markdown(f"👉 **แทนค่า:** $F_{{l}} = {p_l_val:.2f} \\times {area_floor:.2f} \\times 0.00980665 = \\mathbf{{{f_l_val:.2f}\\text{{ kN}}}}$")
            
            st.latex(r"F_{net} = F_{windward} - F_{leeward}")
            st.markdown(f"👉 **แทนค่าหักล้างทิศทาง:** $F_{{net}} = {f_w_val:.2f} - ({f_l_val:.2f})$")
            
            # สรุปผลลัพธ์ที่นำไปคีย์ลงโปรแกรมโครงสร้าง
            st.success(f"🎯 **บทสรุปกำลังชั้น {f['floor']}:** เกิดแรงปะทะด้านข้างรวมสุทธิ **{net_f_story:.2f} kN** กระทำทางราบเข้าสู่ Diaphragm แผ่นพื้นโครงสร้างที่จุดพิกัดความสูงสะสม **z = {f['z_top']:.2f} ม.**")

    st.write("---")

    # ----------------------------------------------------
    # SECTION 4: ตารางสรุปภาพรวมครบทุกตัวแปร (Comprehensive Summary Table)
    # ----------------------------------------------------
    st.subheader("4. ตารางสรุปผลลัพธ์วิเคราะห์แปรผันตามชั้นความสูง (Engineering Data Summary)")
    st.markdown("ตารางนี้ทำการรวบรวมตัวแปรขั้นกลางทั้งหมดเพื่อส่งรายงานคำนวณให้วิศวกรผู้ตรวจสอบไล่สายตาตรวจเช็คได้อย่างรวดเร็ว:")
    
    summary_list = []
    for idx, f in enumerate(floors_data):
        q_z_mid = q * f['Ce']
        if view_opt == "External":
            p_w = f['p_w']; p_l = p_leeward; f_w = f['force_w_ext']; f_l = f['force_l_ext']
        elif view_opt == "Case 1":
            p_w = f['net_w_c1']; p_l = net_l_c1; f_w = f['force_w_c1']; f_l = f['force_l_c1']
        else:
            p_w = f['net_w_c2']; p_l = net_l_c2; f_w = f['force_w_c2']; f_l = f['force_l_c2']
            
        summary_list.append({
            "ระดับชั้น": f"ชั้น {f['floor']}",
            "พิกัดยอดพื้น z_top (ม.)": f"{f['z_top']:.2f}",
            "สัมประสิทธิ์ Ce": f"{f['Ce']:.3f}",
            "แรงลมอ้างอิง qz (kgf/m²)": f"{q_z_mid:.2f}",
            "Net Windward p_w (kgf/m²)": f"{p_w:.2f}",
            "Net Leeward p_l (kgf/m²)": f"{p_l:.2f}",
            "พื้นที่รับลม A (m²)": f"{f['area_front']:.1f}",
            "แรง Windward (kN)": f"{f_w:.2f}",
            "แรง Leeward (kN)": f"{f_l:.2f}",
            "แรงลัพธ์ Point Load (kN)": f"{(f_w - f_l):.2f}"
        })
        
    df_report = pd.DataFrame(summary_list)
    st.dataframe(df_report, use_container_width=True, hide_index=True)
    
    st.info("💡 **หมายเหตุวิศวกรรมการป้อนโหลดข้าง:** ค่าในคอลัมน์ขวาสุด 'แรงลัพธ์ Point Load (kN)' คือค่าแรง Lateral Force รวมผลของฝังรับลมและท้ายลมแล้ว "
             "ซึ่งสามารถนำไปกรอกลงในช่อง Diaphragm Lateral Load หรือป้อนเข้าเป็น Joint Load ประจำพิกัดชั้นความสูงของแบบจำลองโครงสร้างอาคารได้โดยตรง")
