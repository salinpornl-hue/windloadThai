import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# ส่วนคำนวณหลักตามมาตรฐาน มยผ. 1311-50
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q = 0.5 * rho * V^2 (แปลงเป็น kgf/m²)"""
    rho = 1.25 
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665 

def get_Ce(z, exposure):
    """คำนวณค่าประกอบเนื่องจากสภาพภูมิประเทศ (Ce) ตามระดับความสูง"""
    z_eff = max(z, 6.0) # มยผ. กำหนดให้คิดความสูงขั้นต่ำที่ 6 เมตร
    if 'A' in exposure:
        return min(max((z_eff/10.0)**0.20, 0.9), 1.5)
    elif 'B' in exposure:
        return min(max((z_eff/10.0)**0.28, 0.7), 1.2)
    else:
        return min(max((z_eff/10.0)**0.40, 0.5), 1.0)

# ==========================================
# การตั้งค่าหน้าจอแสดงผล (Streamlit UI)
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลมและ Base Shear", layout="wide")
st.title("🌪️ โปรแกรมวิเคราะห์แรงลมและแรงเฉือนฐานอาคารรายชั้น (มยผ. 1311-50)")
st.markdown("---")

# --- ส่วนรับค่าพารามิเตอร์อินพุต (จัดกลุ่มให้กรอกง่ายด้านบน) ---
st.subheader("🚧 1. กำหนดค่าตัวแปรการออกแบบ (Design Inputs)")
col_in1, col_in2, col_in3 = st.columns(3)

with col_in1:
    st.markdown("**📍 ข้อมูลแรงลมและภูมิประเทศ**")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0)
    exposure = st.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง)', 'C (เมือง/ตึกสูง)'], index=1)
    Iw_input = st.selectbox("ค่าประกอบความสำคัญ (Iw)", [1.0, 1.15], index=0)

with col_in2:
    st.markdown("**🏢 มิติแปลนอาคาร**")
    B = st.number_input("ความกว้างอาคารด้านขนานลม B (m)", value=15.0, step=1.0)
    L = st.number_input("ความยาวอาคารตั้งฉากลม L (m)", value=20.0, step=1.0)
    enclosure = st.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])

with col_in3:
    st.markdown("**📐 สัมประสิทธิ์แรงดันลม (Cp)**")
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, step=0.1)
    Cp_w = st.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
    Cp_l = st.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)
    Cp_r = st.number_input("Cp หลังคา (Roof Uplift)", value=-0.7, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# --- ส่วนกำหนดจำนวนชั้นและความสูงรายชั้น ---
st.markdown("---")
st.subheader("🏢 2. ข้อมูลความสูงโครงสร้างรายชั้น (Multi-story Configuration)")
num_stories = st.number_input("จำนวนชั้นของอาคารทั้งหมด", min_value=1, max_value=15, value=3, step=1)

st.markdown("*ระบุความสูงช่วงชั้นโครงสร้างแยกแต่ละชั้น (เมตร):*")
floor_cols = st.columns(num_stories)
floor_heights = []
for i in range(num_stories):
    with floor_cols[i]:
        default_h = 4.0 if i == 0 else 3.5
        h_val = st.number_input(f"ความสูงชั้นที่ {i+1}", min_value=1.0, max_value=10.0, value=default_h, key=f"fh_{i}")
        floor_heights.append(h_val)

# ==========================================
# ส่วนประมวลผลคำนวณเชิงวิศวกรรม
# ==========================================
q = calculate_q(V_input)
H_total = sum(floor_heights)
qh_max = q * get_Ce(H_total, exposure)

# แรงลมภายนอกด้านตามลมและแรงดันภายในอาคาร (อ้างอิงความสูงยอดอาคาร qh ตามมาตรฐาน)
p_leeward = Iw_input * qh_max * Cg_input * Cp_l
p_roof = Iw_input * qh_max * Cg_input * Cp_r
p_internal_pos = qh_max * GCpi
p_internal_neg = qh_max * (-GCpi)

# คำนวณขอบเขตและหน่วยแรงดันแยกรายชั้น
z_current = 0.0
story_data = []

for i in range(num_stories):
    h = floor_heights[i]
    z_bottom = z_current
    z_top = z_current + h
    z_mid = (z_bottom + z_top) / 2.0  # ใช้ความสูงกึ่งกลางชั้นคิดค่า Ce
    
    Ce_i = get_Ce(z_mid, exposure)
    p_windward_i = Iw_input * q * Ce_i * Cg_input * Cp_w
    
    # คำนวณหน่วยแรงดันสุทธิในกรณีวิกฤตที่สุด (ดันเข้า + ดูดออกภายนอก)
    # หมายเหตุ: แรงดันภายใน (Internal Pressure) จะหักล้างกันเองเมื่อคิดแรงรวมทั้งอาคาร (Base Shear)
    # แต่ต้องนำมาคิดแรงสุทธิเมื่อออกแบบชิ้นส่วนผนังรายชั้น
    p_net_windward = p_windward_i - p_internal_neg
    p_net_leeward = p_leeward - p_internal_pos
    
    # พื้นที่รับลมของชั้น (Tributary Area)
    trib_area = L * h
    
    # แรงลมรวมที่กระทำในชั้นนี้ (หน่วย: kgf) -> คิดจากความต่างแรงดันภายนอก Windward และ Leeward
    force_kgf = (p_windward_i - p_leeward) * trib_area
    force_kn = (force_kgf * 9.80665) / 1000.0  # แปลง kgf เป็น kN
    
    story_data.append({
        "story": i + 1,
        "height": h,
        "z_bottom": z_bottom,
        "z_top": z_top,
        "z_mid": z_mid,
        "Ce": Ce_i,
        "p_w": p_windward_i,
        "p_net_w": p_net_windward,
        "trib_area": trib_area,
        "force_kn": force_kn
    })
    z_current = z_top

# คำนวณแรงเฉือนฐานรากสุทธิรวม (Total Base Shear)
total_base_shear_kn = sum([s['force_kn'] for s in story_data])

# ==========================================
# ส่วนแสดงผลลัพธ์เชิงกราฟิก (พล็อตเรียงบน-ล่างแบบเต็มหน้าจอ)
# ==========================================
st.markdown("---")
st.subheader("📊 3. แผนภาพแสดงผลการวิเคราะห์แบบละเอียด (Visualizations)")

# --- แผนภาพที่ 1: หน้าตัดหน่วยแรงลม (Cross Section) ขยายเต็มจอ ---
st.markdown("#### **1. แผนภาพหน่วยแรงดันลมภายนอกบนหน้าตัดอาคาร (Cross Section View: kgf/m²)**")

fig1 = go.Figure()
# วาดกรอบอาคาร
fig1.add_trace(go.Scatter(
    x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0],
    fill="toself", fillcolor="rgba(240, 244, 255, 0.6)",
    line=dict(color="#1E3A8A", width=3.5), name="โครงสร้างอาคาร"
))

# วาดเส้นประแสดงระดับชั้นภายในตึก
for s in story_data[:-1]:
    fig1.add_shape(type="line", x0=0, y0=s['z_top'], x1=B, y1=s['z_top'],
                   line=dict(color="gray", width=1.5, dash="dash"))

# พล็อตลูกศรแรงดันลมรับลม (Windward Arrows) ของแต่ละชั้น
for s in story_data:
    arrow_x_start = -1.5 - (s['p_w'] / 20.0)  # ปรับสเกลความยาวลูกศรตามค่าแรง
    fig1.add_annotation(
        x=0, y=s['z_mid'], ax=arrow_x_start, ay=s['z_mid'],
        xref="x", yref="y", axref="x", ayref="y",
        text=f"<b>{s['p_w']:.1f}</b>", showarrow=True,
        arrowhead=2, arrowsize=1.2, arrowcolor="red", font=dict(color="red", size=12)
    )

# พล็อตลูกศรแรงด้านตามลม (Leeward Arrow)
fig1.add_annotation(
    x=B, y=H_total/2, ax=B + 2.5, ay=H_total/2,
    xref="x", yref="y", axref="x", ayref="y",
    text=f"<b>Leeward: {p_leeward:.1f}</b>", showarrow=True,
    arrowhead=2, arrowsize=1.2, arrowcolor="orange", font=dict(color="orange", size=12)
)

# พล็อตลูกศรแรงยกหลังคา (Roof Uplift Arrow)
fig1.add_annotation(
    x=B/2, y=H_total + 1.2, ax=B/2, ay=H_total,
    xref="x", yref="y", axref="x", ayref="y",
    text=f"<b>Roof Uplift: {p_roof:.1f} kgf/m²</b>", showarrow=True,
    arrowhead=2, arrowsize=1.2, arrowcolor="purple", font=dict(color="purple", size=12)
)

fig1.update_layout(
    xaxis_title="ความกว้างตึก B (ม.)", yaxis_title="ความสูงอาคาร z (ม.)",
    xaxis_range=[-8, B+8], yaxis_range=[-1, H_total+3],
    plot_bgcolor="white", height=500
)
fig1.update_xaxes(showgrid=True, gridcolor='#F3F4F6')
fig1.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# --- แผนภาพที่ 2: ขอบเขตพื้นที่รับลมหน้าตรง (Elevation View) ขยายเต็มจอ ---
st.markdown("#### **2. ขอบเขตพื้นที่รับลมหน้าตรงแยกรายชั้น (Elevation View - ด้านรับลม L)**")

fig2 = go.Figure()
colors = ["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"] # ไล่เฉดสีฟ้าแต่ละชั้น

for idx, s in enumerate(story_data):
    c_fill = colors[idx % len(colors)]
    # วาดบล็อกสี่เหลี่ยมพื้นที่รับลมแต่ละชั้น
    fig2.add_trace(go.Scatter(
        x=[0, L, L, 0, 0], y=[s['z_bottom'], s['z_bottom'], s['z_top'], s['z_top'], s['z_bottom']],
        fill="toself", fillcolor=c_fill, line=dict(color="#1D4ED8", width=1.5),
        showlegend=False
    ))
    # ใส่ป้ายข้อความบอกข้อมูลพื้นที่กึ่งกลางบล็อก
    fig2.add_annotation(
        x=L/2, y=s['z_mid'],
        text=f"<b>ชั้น {s['story']}: Area = {s['trib_area']:.1f} m²</b><br>(กว้าง {L}ม. × สูงช่วงชั้น {s['height']}ม.)",
        showarrow=False, font=dict(color="#1E3A8A", size=12)
    )

fig2.update_layout(
    xaxis_title="ความยาวหน้าแผงผนังรับแรง L (ม.)", yaxis_title="ระดับความสูงของอาคาร z (ม.)",
    yaxis_range=[-1, H_total+2], plot_bgcolor="white", height=500
)
fig2.update_xaxes(showgrid=True, gridcolor='#F3F4F6')
fig2.update_yaxes(showgrid=True, gridcolor='#F3F4F6')
st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# ส่วนแสดงรายงานการคำนวณและสรุป Base Shear
# ==========================================
st.markdown("---")
st.subheader("📑 4. รายการคำนวณและสรุปแรงเฉือนฐานอาคาร (Calculation Book & Base Shear)")

# แสดงกล่องสรุปแรงเฉือนรวมที่ฐานอาคารเด่นชัด
st.metric(label="💥 แรงเฉือนที่ฐานอาคารรวมทั้งหมดเนื่องจากแรงลม (Total Base Shear - V_base)", value=f"{total_base_shear_kn:.2f} kN")

report = f"""
### **รายการคำนวณเชิงวิศวกรรม (Engineering Report)**
* **มาตรฐานอ้างอิง:** มาตรฐาน มยผ. 1311-50
* **รูปทรงและพื้นที่โครงสร้าง:** กว้าง $B$ = {B} ม., ยาว $L$ = {L} ม., ความสูงรวม = {H_total:.2f} ม. (${num_stories}$ ชั้น)

#### **1. ตัวแปรอ้างอิงแรงดันลมทางอุตุนิยมวิทยา**
* ความเร็วลมออกแบบพื้นฐาน ($V$) = **{V_input} m/s**
* หน่วยแรงลมอ้างอิงคำนวณได้ ($q$) = $\\frac{{0.5 \\cdot 1.25 \\cdot {V_input}^2}}{{9.80665}}$ = **{q:.2f} kgf/m²**
* สภาพภูมิประเทศเลือกใช้คลาส = **{exposure}**
* ค่าตัวคูณแรงลมกระโชก ($C_g$) = **{Cg_input}**

#### **2. ตารางแสดงผลการคำนวณหน่วยแรงและแรงลัพธ์สะสมรายชั้น**
ต่อไปนี้คือตารางสรุปพารามิเตอร์ $C_e$, แรงดันลมที่ผนัง และการส่งถ่ายแรงลัพธ์รายชั้นเข้าสู่โครงสร้างหลัก:
"""
st.markdown(report)

# สร้าง DataFrame ตารางเพื่อสรุปตัวเลขให้อ่านและคัดลอกง่าย
table_rows = []
for s in story_data:
    table_rows.append({
        "ชั้นที่": f"ชั้น {s['story']}",
        "ความสูงช่วง (ม.)": s['height'],
        "ระดับพิกัด z (ม.)": f"{s['z_bottom']:.1f} ถึง {s['z_top']:.1f}",
        "สัมประสิทธิ์ Ce": round(s['Ce'], 3),
        "Windward (kgf/m²)": round(s['p_w'], 1),
        "Leeward (kgf/m²)": round(p_leeward, 1),
        "พื้นที่รับลม A (m²)": round(s['trib_area'], 1),
        "แรงลัพธ์ประจำชั้น (kN)": round(s['force_kn'], 2)
    })
df_report = pd.DataFrame(table_rows)
st.dataframe(df_report, use_container_width=True, hide_index=True)

# วิธีทำคำนวณ Base Shear ทีละสเต็ปอย่างละเอียด
st.markdown("#### **3. ขั้นตอนการคำนวณแรงเฉือนฐานอาคารสุทธิ ($V_{{base}}$)**")
st.markdown("แรงเฉือนฐานรวมเกิดจากการสะสมแรงลมกระทำภายนอกของผนังรับลม (Windward) และผนังตามลม (Leeward) ของทุกชั้นโครงสร้างเข้าด้วยกัน:")

math_steps = ""
for s in story_data:
    math_steps += f"""
* **ชั้นที่ {s['story']}:** * สมการ: $F_{s['story']} = (p_{{windward}} - p_{{leeward}}) \\times A_{{trib}} \\times \\frac{{9.80665}}{{1000}}$
  * แทนค่า: $F_{s['story']} = ({s['p_w']:.2f} - ({p_leeward:.2f})) \\times {s['trib_area']:.1f} \\times 0.00980665$ = **{s['force_kn']:.2f} kN**
"""
st.markdown(math_steps)

st.markdown(f"""
---
**⚡ ผลรวมสมการแรงเฉือนฐานรากสุทธิ ($V_{{base}}$):**
$$V_{{base}} = \\sum F_i = F_1 + F_2 + ... + F_n$$
$$V_{{base}} = { ' + '.join([f'{s["force_kn"]:.2f}' for s in story_data]) }$$
$$V_{{base}} = \\mathbf{{{total_base_shear_kn:.2f}\\text{{ kN}}}}$$

*หมายเหตุ: ในการคำนวณสมดุลแรงเฉือนรวมของโครงสร้างอาคาร แรงดันลมภายใน ($p_{{internal}}$) จะมีขนาดเท่ากันแต่ทิศทางตรงกันข้ามกระทำยันผนังภายในทั้งสองฝั่ง จึงหักล้างกันเองหมดไปโดยปริยาย ทำให้ค่าแรงเฉือนฐานรากคิดสมบูรณ์จากผลต่างแรงภายนอกได้อย่างแม่นยำ*
""")
