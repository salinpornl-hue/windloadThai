import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# Core Logic & Math (มยผ. 1311-50)
# ==========================================
def calculate_q(V):
    """คำนวณหน่วยแรงลมอ้างอิง q = 0.5 * rho * V^2"""
    rho = 1.25 # ความหนาแน่นอากาศ (kg/m^3)
    q_pa = 0.5 * rho * (V ** 2)
    return q_pa / 9.80665 # แปลงเป็น kgf/m^2

def get_Ce_details(z, exposure):
    """คำนวณ Ce อิงตาม Power Law และคืนค่าวิธีคิดโดยละเอียด"""
    z_eff = max(z, 6.0) # ต่ำสุด 6 เมตรตาม มยผ.
    if 'A' in exposure:
        alpha = 0.20
        min_val, max_val = 0.9, 1.5
    elif 'B' in exposure:
        alpha = 0.28
        min_val, max_val = 0.7, 1.2
    else:
        alpha = 0.40
        min_val, max_val = 0.5, 1.0
        
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    
    explanation = f"ใช้สูตรสภาพภูมิประเทศ {exposure}: (z_eff/10)^{alpha} = ({z_eff}/10)^{alpha} = {raw_ce:.4f} -> ควบคุมด้วยค่าวิกฤตได้ {ce:.3f}"
    if z < 6.0:
        explanation = f"เนื่องจากความสูง z = {z} ม. ต่ำกว่า 6.0 ม. ให้ใช้ z = 6.0 ม. ในการคำนวณ | " + explanation
        
    return ce, explanation

# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="โปรแกรมคำนวณแรงลม มยผ. 1311-50 (ละเอียดพิเศษ)", layout="wide")
st.title("🌪️ โปรแกรมคำนวณแรงลมออกแบบแยกรายชั้น (มยผ. 1311-50)")
st.subheader("🏢 สำหรับอาคารหลังคาแบนที่มีความสูงแต่ละชั้นไม่เท่ากัน")
st.markdown("---")

# --- รับค่าตัวแปร ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📍 1. ข้อมูลสถานที่ & ข้อกำหนดกำหนดลม")
    V_input = st.number_input("ความเร็วลมพื้นฐาน V (m/s)", value=25.0, step=1.0, help="ความเร็วลมเฉลี่ย 50 ปี ตามจังหวัดที่ตั้ง")
    exposure = st.selectbox("สภาพภูมิประเทศ (Exposure)", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง/ต้นไม้เยอะ)', 'C (ในเมือง/ตึกสูงหนาแน่น)'])
    Iw_input = st.selectbox("ค่าประกอบความสำคัญ (Iw)", [1.0, 1.15], index=0, help="1.0 = อาคารทั่วไป, 1.15 = อาคารสำคัญ/สาธารณะ")

with col2:
    st.markdown("### 🏢 2. มิติอาคารหลัก")
    B = st.number_input("ความกว้างอาคารด้านขนานลม B (m)", value=15.0, min_value=1.0)
    L = st.number_input("ความยาวอาคารตั้งฉากลม L (m)", value=20.0, min_value=1.0)
    
    st.markdown("#### 📐 กำหนดความสูงแยกแต่ละชั้น")
    num_stories = st.number_input("จำนวนชั้นทั้งหมด", value=3, step=1, min_value=1)
    
    # วนลูปสร้างช่องกรอกความสูงแต่ละชั้นแบบไดนามิก
    floor_heights = []
    for i in range(num_stories):
        # กำหนดค่าเริ่มต้นให้ชั้น 1 สูงกว่าชั้นอื่นตามพฤติกรรมอาคารทั่วไป
        default_h = 4.0 if i == 0 else 3.5
        h_val = st.number_input(f"ความสูงของ ชั้นที่ {i+1} (เมตร)", value=default_h, min_value=1.0, key=f"h_floor_{i}")
        floor_heights.append(h_val)
        
    # คำนวณความสูงสะสมรวม (H)
    H_total = sum(floor_heights)
    st.info(f"📊 ความสูงอาคารรวมสะสม (H) = **{H_total:.2f} เมตร**")

with col3:
    st.markdown("### 🌬️ 3. สัมประสิทธิ์แรงดันลม")
    enclosure = st.selectbox("ลักษณะการปิดล้อมอาคาร", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially Enclosed)"])
    Cg_input = st.number_input("ค่าประกอบลมกระโชก (Cg)", value=2.0, help="ปกติใช้ 2.0 สำหรับโครงสร้างหลัก")
    Cp_w = st.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8)
    Cp_l = st.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5)

# ตั้งค่า GCpi ตามประเภทอาคาร
GCpi = 0.55 if "Partially" in enclosure else 0.18

st.markdown("---")

if st.button("🚀 ประมวลผลและสร้างเล่มรายการคำนวณอย่างละเอียด", use_container_width=True):
    
    # 1. คำนวณค่าพื้นฐานหลัก
    q = calculate_q(V_input)
    Ce_H, Ce_H_exp = get_Ce_details(H_total, exposure)
    qh = q * Ce_H
    
    # 2. คำนวณระดับความสูงสะสม และค่าที่เกิดขึ้นในแต่ละชั้น
    z_cumulative = 0
    floors_data = []
    
    for i in range(num_stories):
        h_current = floor_heights[i]
        z_bottom = z_cumulative
        z_top = z_cumulative + h_current
        z_mid = (z_bottom + z_top) / 2.0 # คำนวณหา Ce ที่กึ่งกลางชั้น
        
        Ce_mid, Ce_mid_exp = get_Ce_details(z_mid, exposure)
        p_w_z = Iw_input * q * Ce_mid * Cg_input * Cp_w
        
        floors_data.append({
            "floor_num": i + 1,
            "height": h_current,
            "z_bottom": z_bottom,
            "z_top": z_top,
            "z_mid": z_mid,
            "Ce": Ce_mid,
            "Ce_exp": Ce_mid_exp,
            "p_windward": p_w_z
        })
        z_cumulative = z_top

    # คำนวณแรงลมด้านอื่น ๆ
    p_leeward = Iw_input * qh * Cg_input * Cp_l 
    p_internal_pos = qh * GCpi
    p_internal_neg = qh * (-GCpi)

    # ==========================================
    # 1. แสดงรูปภาพประกอบมิติอาคารและแรงลม (Plotly)
    # ==========================================
    st.subheader("📐 แผนภาพโครงสร้างและแรงลมจำลอง (Dimension & Wind Pressure Schematic)")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=[0, B, B, 0, 0], 
        y=[0, 0, H_total, H_total, 0], 
        fill="toself", fillcolor="rgba(240, 245, 255, 0.6)",
        line=dict(color="navy", width=3), name="โครงสร้างอาคาร"
    ))
    
    for f in floors_data:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'],
                      line=dict(color="rgba(0,0,128,0.25)", width=1.5, dash="dash"))
        fig.add_annotation(x=B + 0.5, y=f['z_top'], text=f"z = {f['z_top']:.2f} m", 
                           showarrow=False, xanchor="left", font=dict(size=11, color="blue"))
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"Floor {f['floor_num']} (h={f['height']}m)", 
                           showarrow=False, font=dict(size=12, color="gray", style="italic"))
        
        arrow_scale = 1 + (f['p_windward'] / 50.0) 
        fig.add_annotation(x=0, y=f['z_mid'], ax=-arrow_scale, ay=f['z_mid'], xref="x", yref="y", axref="x", ayref="y",
                           text=f"{f['p_windward']:.1f} kgf/m²", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="red",
                           font=dict(color="red", size=10), xanchor="right")

    fig.add_annotation(x=B + 4.5, y=H_total/2, ax=B, ay=H_total/2, xref="x", yref="y", axref="x", ayref="y",
                       text=f"Leeward: {p_leeward:.1f} kgf/m²<br>(คงที่ตลอดความสูง)", showarrow=True, 
                       arrowhead=2, arrowsize=1.2, arrowcolor="orange", font=dict(color="orange", size=11))

    fig.update_layout(
        title=dict(text=f"รูปตัดอาคารแสดงแรงดันลมออกแบบ (ความกว้าง B = {B} ม., ความสูงรวม H = {H_total} ม.)", x=0.5),
        xaxis_title="ความกว้างอาคารแนวขนานลม B (เมตร)", 
        yaxis_title="ระดับความสูงจากพื้นดิน z (เมตร)", 
        yaxis_range=[-1, H_total + 3], 
        xaxis_range=[-7, B + 7], 
        height=550,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 2. เล่มรายการคำนวณอย่างละเอียด (Calculation Report)
    # ==========================================
    st.subheader("📑 เล่มรายการคำนวณโดยละเอียด (Comprehensive Calculation Report)")
    
    st.markdown(f"""
    ### **[ส่วนที่ 1]: ข้อมูลโครงการและตัวแปรตั้งต้น**
    * **ข้อกำหนดการคำนวณ:** อ้างอิงมาตรฐาน มยผ. 1311-50 (มาตรฐานการคำนวณแรงลมและการตอบสนองของโครงสร้าง)
    * **ประเภทโครงสร้าง:** ระบบโครงสร้างหลักต้านทานแรงลม (Main Wind Force Resisting System: MWFRS)
    * **ลักษณะอาคาร:** รูปทรงสี่เหลี่ยมหลังคาแบน จำนวน **{num_stories} ชั้น** มีมิติดังนี้:
      * ความกว้างด้านขนานลม ($B$) = `{B:.2f}` เมตร
      * ความยาวด้านตั้งฉากลม ($L$) = `{L:.2f}` เมตร
      * ความสูงรวมถึงยอดอาคาร ($H$) = `{H_total:.2f}` เมตร (คำนวณจากผลรวมของแต่ละชั้นจริง)
    
    ---
    ### **[ส่วนที่ 2]: การคำนวณหน่วยแรงลมอ้างอิง (Velocity Pressure, $q$)**
    หน่วยแรงลมอ้างอิงคำนวณจากความหนาแน่นของอากาศที่สภาวะมาตรฐานและความเร็วลมออกแบบ:
    * สมการหลัก: $$q = \\frac{{0.5 \\cdot \\rho \\cdot V^2}}{{g}}$$
    * แทนค่าตัวแปร:
      * ความเร็วลมพื้นฐาน ($V$) = `{V_input:.2f}` m/s
      * ความหนาแน่นอากาศ ($\\rho$) = `1.25` $kg/m^3$
      * แรงโน้มถ่วงมาตรฐาน ($g$) = `9.80665` $m/s^2$ (เพื่อแปลงหน่วยจาก Pascal เป็น $kgf/m^2$)
    * **ขั้นตอนการคำนวณ:**
      $$q = \\frac{{0.5 \\cdot 1.25 \\cdot ({V_input:.2f})^2}}{{9.80665}}$$
      $$q = \\frac{{0.5 \\cdot 1.25 \\cdot {V_input**2:.2f}}}{{9.80665}} = \\frac{{{0.5 * 1.25 * (V_input**2):.4f}}}{{9.80665}}$$
      $$q = {q:.4f} \\text{{ kgf/m}}^2$$
    
    ---
    ### **[ส่วนที่ 3]: สัมประสิทธิ์ประกอบการออกแบบคงที่**
    * ค่าประกอบความสำคัญของแรงลม ($I_w$) = `{Iw_input:.2f}`
    * สภาพภูมิประเทศที่ตั้งอาคาร = `ประเภท {exposure}`
    * ค่าประกอบลมกระโชก ($C_g$) = `{Cg_input:.2f}`
    * สัมประสิทธิ์แรงดันภายในอาคาร ($GC_{{pi}}$): เนื่องจากเลือกประเภท `{enclosure}` 
      * ค่าประกอบ $GC_{{pi}}$ สุทธิ = `±{GCpi:.2f}` (ต้องคิดทั้งกรณีแรงอัดภายใน [+] และแรงดูดภายใน [-])
    * สัมประสิทธิ์แรงดันภายนอกด้านตามลม ($C_p \\text{{ Leeward}}$) = `{Cp_l:.2f}`
    * สัมประสิทธิ์แรงดันภายนอกด้านรับลม ($C_p \\text{{ Windward}}$) = `{Cp_w:.2f}`
    """)
    
    st.markdown(r"### **[ส่วนที่ 4]: การคำนวณหน่วยแรงลมภายนอกด้านรับลมแยกรายชั้น (Windward Pressure Profile)**")
    st.markdown(r"สมการคำนวณแรงลมภายนอก: $$p_{ext} = I_w \cdot q \cdot C_e \cdot C_g \cdot C_p$$")
    st.markdown("*(หมายเหตุ: สำหรับโครงสร้างหลายชั้น ค่า $C_e$ จะแปรผันตามระดับความสูงกึ่งกลางของชั้นนั้นๆ ทำให้แรงลมเพิ่มขึ้นตามความสูง)*")
    
    for f in floors_data:
        with st.expander(f"🔍 ดูสูตรการคำนวณโดยละเอียดอย่างเป็นขั้นตอนของ: ชั้นที่ {f['floor_num']}", expanded=True):
            st.markdown(f"""
            **1. ตรวจสอบระดับความสูงของ ชั้นที่ {f['floor_num']}**
            * ระดับท้องพื้น (Bottom) = `{f['z_bottom']:.2f}` ม. | ระดับหลังพื้น (Top) = `{f['z_top']:.2f}` ม.
            * ระดับความสูงอ้างอิงกึ่งกลางชั้น ($z_{{mid}}$) = `({f['z_bottom']:.2f} + {f['z_top']:.2f}) / 2` = **`{f['z_mid']:.2f}` ม.**
            
            **2. คำนวณสัมประสิทธิ์การเปิดโล่ง ($C_e$) ของชั้นนี้**
            * วิธีคิด: {f['Ce_exp']}
            * ผลลัพธ์ได้ค่า $C_e$ ประจำชั้นที่ = **`{f['Ce']:.3f}`**
            
            **3. แทนค่าคำนวณหน่วยแรงลมภายนอกด้านรับลม ($p_w$)**
            * แทนค่าลงในสมการ: $p_w = I_w \\cdot q \\cdot C_e \\cdot C_g \\cdot C_p$
            * ตัวเลขที่ใช้แทนค่า: $p_w = {Iw_input:.2f} \\cdot {q:.2f} \\cdot {f['Ce']:.3f} \\cdot {Cg_input:.2f} \\cdot ({Cp_w:.2f})$
            * คำนวณผลลัพธ์ทีละสเต็ป:
              * ขั้นที่ 1 (คูณสัมประสิทธิ์ภายนอกทั้งหมด): ${Iw_input:.2f} \\cdot {q:.4f} \\cdot {f['Ce']:.3f} \\cdot {Cg_input:.2f} = {Iw_input * q * f['Ce'] * Cg_input:.4f}$
              * ขั้นที่ 2 (คูณกับค่า $C_p$ ผนัง): ${Iw_input * q * f['Ce'] * Cg_input:.4f} \\cdot {Cp_w:.2f}$
              * **หน่วยแรงลมภายนอกสุทธิประจำชั้นที่ {f['floor_num']} ($p_w$) = `{f['p_windward']:.2f}` kgf/m²**
            """)

    st.markdown(f"""
    ---
    ### **[ส่วนที่ 5]: การคำนวณหน่วยแรงลมภายนอกด้านตามลม (Leeward) และแรงดันภายใน (Internal)**
    ตามมาตรฐาน มยผ. แรงลมด้านตามลมและแรงดันภายในอาคารจะอ้างอิงความดันลมอ้างอิงที่ยอดอาคารสูงสุด ($H = {H_total:.2f}$ ม.) และมีค่าคงที่ตลอดความสูงโครงสร้าง
    
    * **1. หาค่าประกอบที่ความสูงยอดอาคาร ($H = {H_total:.2f}$ ม.):**
      * ค่า $C_e$ ที่ยอดอาคารอ้างอิงสูตร {exposure} = **`{Ce_H:.3f}`** *(วิธีคำนวณ: {Ce_H_exp})*
      * ค่าแรงลมอ้างอิงที่ยอดอาคาร ($q_h$) = $q \\cdot C_e \\text{{(ยอด)}} = {q:.2f} \\cdot {Ce_H:.3f}$ = **`{qh:.2f}` kgf/m²**
      
    * **2. คำนวณหน่วยแรงลมด้านตามลม (Leeward Pressure: $p_l$)**
      * สมการ: $p_l = I_w \\cdot q_h \\cdot C_g \\cdot C_p \\text{{ (Leeward)}}$
      * แทนค่าตัวเลข: $p_l = {Iw_input:.2f} \\cdot {qh:.2f} \\cdot {Cg_input:.2f} \\cdot ({Cp_l:.2f})$
      * ผลลัพธ์: $p_l = {Iw_input * qh * Cg_input:.3f} \\cdot ({Cp_l:.2f})$ = **`{p_leeward:.2f}` kgf/m²** *(เครื่องหมายลบแสดงถึงแรงดูดออกนอกผิวอาคาร)*
      
    * **3. คำนวณหน่วยแรงลมภายในอาคาร (Internal Pressure: $p_{{int}}$)**
      * สมการ: $p_{{int}} = q_h \\cdot (GC_{{pi}})$
      * **กรณีแรงดันภายในเป็นบวก (Internal Push):** $p_{{int+}} = {qh:.2f} \\cdot (+{GCpi:.2f})$ = **`{p_internal_pos:.2f}` kgf/m²** *(ดันออกรอบทิศทาง)*
      * **กรณีแรงดันภายในเป็นลบ (Internal Suction):** $p_{{int-}} = {qh:.2f} \\cdot (-{GCpi:.2f})$ = **`{p_internal_neg:.2f}` kgf/m²** *(ดูดเข้าหาจุดศูนย์กลาง)*
    """)

    st.markdown(r"---")
    st.markdown(r"### **[ส่วนที่ 6]: สรุปผลหน่วยแรงลมสุทธิแยกตาม Load Cases สำหรับนำไปคำนวณออกแบบ**")
    st.markdown(r"ในการออกแบบ วิศวกรต้องนำกรณีแรงลมภายนอกมาหักล้าง/รวมกับแรงลมภายในอาคาร ($p_{net} = p_{ext} - p_{int}$) ซึ่งจะแบ่งออกเป็น 2 กรณีหลักที่วิกฤตที่สุดดังนี้:")
    
    summary_rows = []
    for f in floors_data:
        p_w = f['p_windward']
        net_w_case1 = p_w - p_internal_neg 
        net_w_case2 = p_w - p_internal_pos
        
        summary_rows.append({
            "ชั้นที่": f['floor_num'],
            "ช่วงระดับความสูง (ม.)": f"{f['z_bottom']:.2f} ถึง {f['z_top']:.2f}",
            "P_Windward ภายนอก (kgf/m²)": round(p_w, 2),
            "กรณีวิกฤต 1: ลมรับอัดสุทธิ (p_ext - p_int-)": round(net_w_case1, 2),
            "กรณีวิกฤต 2: ลมรับอัดสุทธิ (p_ext - p_int+)": round(net_w_case2, 2)
        })
        
    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    
    st.markdown(f"""
    * **ข้อสรุปเพิ่มเติมสำหรับผนังด้านตามลม (Leeward สรุปสุทธิ):**
      * แรงลมภายนอกคงที่ที่ยอดอาคาร = `{p_leeward:.2f}` kgf/m²
      * **กรณีวิกฤตสูงสุด (แรงดูดออกภายนอกรวมกับแรงดันบวกภายในดันส่งผลเสริมกัน):** $p_{{net}} = p_l - p_{{int+}} = {p_leeward:.2f} - ({p_internal_pos:.2f})$ = **`{(p_leeward - p_internal_pos):.2f}` kgf/m²** *(แรงดูดดึงผนังหลุดออกนอกอาคารวิกฤตสุด)*
    """)
    st.success("✨ สรุปรายการคำนวณเสร็จสมบูรณ์เรียบร้อย คุณสามารถสั่ง Copy หน้าต่างนี้หรือนำตารางไปประกอบรายการคำนวณวิศวกรรมได้ทันทีครับ")
