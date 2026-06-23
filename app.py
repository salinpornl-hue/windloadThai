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
Cp_s = st.sidebar.number_input("Cp ด้านข้าง (Sidewall)", value=-0.7, step=0.05)
Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Roof)", value=-0.7, step=0.05)
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

# โหลดคงที่อิงยอดอาคาร
p_leeward = Iw_input * qh * Cg_input * Cp_l 
p_sidewall = Iw_input * qh * Cg_input * Cp_s
p_roof = Iw_input * qh * Cg_input * Cp_r
p_int_pos = qh * GCpi     
p_int_neg = qh * (-GCpi)  

# Net โหลดคงที่
net_l_c1, net_l_c2 = p_leeward - p_int_neg, p_leeward - p_int_pos
net_s_c1, net_s_c2 = p_sidewall - p_int_neg, p_sidewall - p_int_pos
net_r_c1, net_r_c2 = p_roof - p_int_neg, p_roof - p_int_pos

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
    area_side = B * h   # พื้นที่ผนังด้านข้าง
    
    # Story Force (kN) = (Net Windward - Net Leeward) * Area * 0.00980665
    force_c1 = (net_w_c1 - net_l_c1) * area_front * 0.00980665
    force_c2 = (net_w_c2 - net_l_c2) * area_front * 0.00980665
    
    floors_data.append({
        "floor": i+1, "h": h, "z_bot": z_bot, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_exp, "p_w": p_w,
        "net_w_c1": net_w_c1, "net_w_c2": net_w_c2,
        "area_front": area_front, "area_side": area_side,
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
def plot_cross_section(floors, mode):
    fig = go.Figure()
    # วาดรูปอาคาร
    fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), name="โครงสร้าง"))
    
    def add_arrow(x_surf, y_pos, val, face):
        arr_len = 1.5 + abs(val)/35.0
        if face == "windward": # ซ้าย
            if val >= 0: ax, ay, x, y, col, x_anc = -arr_len, y_pos, 0, y_pos, "#DC2626", "right" # อัดเข้า
            else: ax, ay, x, y, col, x_anc = 0, y_pos, -arr_len, y_pos, "#9333EA", "left" # ดูดออก
        elif face == "leeward": # ขวา
            if val >= 0: ax, ay, x, y, col, x_anc = B+arr_len, y_pos, B, y_pos, "#DC2626", "left" # อัดเข้า (ซ้าย)
            else: ax, ay, x, y, col, x_anc = B, y_pos, B+arr_len, y_pos, "#EA580C", "right" # ดูดออก (ขวา)
        elif face == "roof": # บน
            ax, ay, x, y, col, x_anc = x_surf, H_total+(arr_len), x_surf, H_total, "#9333EA", "center" # ดูดขึ้น
            
        fig.add_annotation(x=x, y=y, ax=ax, ay=ay, xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{val:.1f}</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor=col, font=dict(color=col, size=13), xanchor=x_anc)

    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="gray", width=1, dash="dash"))
        val_w = f['p_w'] if mode == "External" else (f['net_w_c1'] if mode == "Case 1" else f['net_w_c2'])
        add_arrow(0, f['z_mid'], val_w, "windward")
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"ชั้น {f['floor']}", showarrow=False, font=dict(color="#4B5563"))

    val_l = p_leeward if mode == "External" else (net_l_c1 if mode == "Case 1" else net_l_c2)
    add_arrow(B, H_total/2, val_l, "leeward")
    
    val_r = p_roof if mode == "External" else (net_r_c1 if mode == "Case 1" else net_r_c2)
    add_arrow(B/2, H_total, val_r, "roof")

    fig.update_layout(title=f"<b>1. แผนภาพหน้าตัดแรงดันลม (Cross Section) - โหมด {mode}</b>", xaxis_title="ความกว้างอาคาร B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)", xaxis_range=[-7, B+7], yaxis_range=[-1, H_total+4], height=500, plot_bgcolor="white", margin=dict(t=40,b=20))
    fig.update_xaxes(showgrid=True, gridcolor='#F3F4F6'); fig.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
    return fig

def plot_elevation(floors, length_dim, label):
    fig = go.Figure()
    colors = ["#93C5FD", "#60A5FA", "#3B82F6", "#2563EB"]
    for idx, f in enumerate(floors):
        area = f['area_front'] if "Front" in label else f['area_side']
        fig.add_trace(go.Scatter(x=[0, length_dim, length_dim, 0, 0], y=[f['z_bot'], f['z_bot'], f['z_top'], f['z_top'], f['z_bot']],
            fill="toself", fillcolor=colors[idx % 4], line=dict(color="#1E3A8A", width=1.5), showlegend=False))
        fig.add_annotation(x=length_dim/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}: Area = {area:.1f} m²</b><br>(กว้าง {length_dim}ม. × สูงช่วงชั้น {f['h']}ม.)", showarrow=False, font=dict(color="white", size=14))
    
    fig.update_layout(title=f"<b>2. ขอบเขตพื้นที่รับลมหน้าตรง Tributary Area ({label})</b>", xaxis_title="ความยาวหน้าแผง (ม.)", yaxis_title="ความสูง (ม.)", height=500, plot_bgcolor="white", margin=dict(t=40,b=20))
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
    view_opt = st.radio("🔘 **เลือกกรณีโหลด (Load Case) เพื่อสั่งวาดแผนภาพทุกรูปแบบอัตโนมัติ:**", 
                        ["External", "Case 1", "Case 2"], 
                        captions=["แรงลมภายนอก 100%", "สุทธิ Case 1: ผสมแรงดูดภายใน (-)", "สุทธิ Case 2: ผสมแรงดันภายใน (+)"], horizontal=True)
    
    # วาดเรียงบนล่าง (Full Width) ตามคำขอ
    st.plotly_chart(plot_cross_section(floors_data, view_opt), use_container_width=True)
    st.markdown("---")
    st.plotly_chart(plot_elevation(floors_data, L, "Front View - ตั้งฉากลม L"), use_container_width=True)
    st.markdown("---")
    st.plotly_chart(plot_elevation(floors_data, B, "Side View - ด้านข้างขนานลม B"), use_container_width=True)

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

# --- TAB 3: Calculation & Export ---
with tab3:
    st.markdown("#### 📑 เล่มรายการคำนวณและตารางโหลด (Engineering Calculation Report)")
    
    # ตารางส่งออก
    df_out = pd.DataFrame([{
        "ชั้น": f"Floor {f['floor']}", "ความสูงพิจารณา (ม.)": f"{f['z_bot']:.1f}-{f['z_top']:.1f}", 
        "Area Front (m²)": round(f['area_front'],1), "Net Windward C1 (kgf/m²)": round(f['net_w_c1'],1), "Net Leeward C1 (kgf/m²)": round(net_l_c1,1),
        "🔥 Story Force C1 (kN)": round(f['force_c1'],2), "Net Windward C2 (kgf/m²)": round(f['net_w_c2'],1), "Net Leeward C2 (kgf/m²)": round(net_l_c2,1),
        "🔥 Story Force C2 (kN)": round(f['force_c2'],2)
    } for f in floors_data])
    st.dataframe(df_out, use_container_width=True, hide_index=True)
    st.download_button("📥 ดาวน์โหลดตาราง CSV", df_out.to_csv(index=False).encode('utf-8-sig'), "Wind_Seismic_Data.csv", "text/csv")
    
    st.markdown("---")
    st.markdown(f"""
    **1. สมการอ้างอิงพื้นฐาน**
    * $V = {V_input}$ m/s $\\rightarrow q = 0.5 \\times 1.25 \\times V^2 / 9.80665 =$ **`{q:.2f}` kgf/m²**
    * ยอดอาคาร ($H = {H_total:.2f}$ ม.) $\\rightarrow C_{{e,h}} = {Ce_H:.3f} \\rightarrow q_h =$ **`{qh:.2f}` kgf/m²**
    
    **2. โหลดคงที่ด้านตามลมและหลังคา**
    * ผนังตามลม (Leeward): $p_l = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_l}) =$ **`{p_leeward:.2f}` kgf/m²**
    * หลังคา (Roof): $p_r = {Iw_input} \\times {qh:.2f} \\times {Cg_input} \\times ({Cp_r}) =$ **`{p_roof:.2f}` kgf/m²**
    """)
    
    st.markdown("##### 🧮 การคำนวณแปลงหน่วย ($kgf/m^2 \\rightarrow kN$) และรวมเป็น Base Shear:")
    for f in floors_data:
        with st.expander(f"🔍 ดูวิธีทำ: ชั้น {f['floor']} (พื้นที่ $A_{{trib}}$ = {f['area_front']:.1f} m²)", expanded=False):
            st.markdown(f"""
            **กรณีที่ 1 (+ แรงดูดภายในอาคาร $p_{{int-}} = {p_int_neg:.2f}$ kgf/m²):**
            * สุทธิฝั่งรับลม $p_{{net, w}} = {f['p_w']:.2f} - ({p_int_neg:.2f}) = {f['net_w_c1']:.2f}$ kgf/m²
            * สุทธิฝั่งตามลม $p_{{net, l}} = {p_leeward:.2f} - ({p_int_neg:.2f}) = {net_l_c1:.2f}$ kgf/m²
            * **Story Force:** $F_{{C1}} = (p_{{net,w}} - p_{{net,l}}) \\times A_{{trib}} \\times 0.00980665$
            * $F_{{C1}} = ({f['net_w_c1']:.2f} - ({net_l_c1:.2f})) \\times {f['area_front']:.1f} \\times 0.00980665 =$ **`{f['force_c1']:.2f}` kN**
            
            **กรณีที่ 2 (+ แรงดันภายในอาคาร $p_{{int+}} = {p_int_pos:.2f}$ kgf/m²):**
            * สุทธิฝั่งรับลม $p_{{net, w}} = {f['p_w']:.2f} - ({p_int_pos:.2f}) = {f['net_w_c2']:.2f}$ kgf/m²
            * สุทธิฝั่งตามลม $p_{{net, l}} = {p_leeward:.2f} - ({p_int_pos:.2f}) = {net_l_c2:.2f}$ kgf/m²
            * **Story Force:** $F_{{C2}} = ({f['net_w_c2']:.2f} - ({net_l_c2:.2f})) \\times {f['area_front']:.1f} \\times 0.00980665 =$ **`{f['force_c2']:.2f}` kN**
            """)
            
    st.success(f"**สมการรวมแรงเฉือนฐาน (Base Shear):** $V_{{wind}} = \\sum F_{{story}} =$ **{V_wind_max:.2f} kN**")
