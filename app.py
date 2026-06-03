import streamlit as st
import ezdxf
import math
import os
import sys
import io
import tempfile
import matplotlib.pyplot as plt
from contextlib import redirect_stdout
from ezdxf.enums import TextEntityAlignment
from import_ezdxf_fi import run_dxf_processing

# Set Streamlit Page Config
st.set_page_config(
    page_title="DXF Beam Perpendicular Generator",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4f46e5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4338ca;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #4f46e5;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

def render_dxf_modelspace(doc):
    try:
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib.pyplot as plt
        
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111)
        
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(doc.modelspace())
        
        ax.set_aspect('equal')
        ax.set_axis_off()
        plt.tight_layout()
        return fig
    except Exception as e:
        st.warning(f"Failed to generate layout preview: {e}")
        return None

# Streamlit Layout Construction
st.title("🏗️ DXF Beam Perpendicular Generator")
st.write("Upload a DXF structural layout drawing, customize processing limits, and download generated perpendicular dimensions.")

# Sidebar Panel for Parameters
st.sidebar.header("⚙️ Configuration Settings")

with st.sidebar.expander("📍 Target Layer & Naming", expanded=True):
    target_layer_in = st.text_input("Target Layer Name", value="RCC_BEAMS", help="Layer name containing beams to process.")
    generated_layer_in = st.text_input("Generated Layer Name", value="GENERATED_PERP_LINES", help="Layer name for perpendicular offset lines.")

with st.sidebar.expander("📏 Distance Ranges (mm)", expanded=True):
    behind_min_in = st.number_input("Behind Min Distance (mm)", value=10, min_value=0, help="Min distance behind the beam to search.")
    behind_max_in = st.number_input("Behind Max Distance (mm)", value=450, min_value=0, help="Max distance behind the beam to search.")
    front_min_in = st.number_input("Front Min Distance (mm)", value=200, min_value=0, help="Min distance in front of the beam.")

with st.sidebar.expander("🎛️ Geometry & Tolerances", expanded=False):
    ratio_in = st.slider("Perp Offset Ratio", min_value=0.05, max_value=0.50, value=0.20, step=0.01, help="Ratio of beam spacing/length for perpendicular ticks.")
    wall_size_tol_in = st.slider("Wall Size Tolerance (%)", min_value=10, max_value=100, value=50, step=5, help="Tolerance for matching wall dimensions.")
    parallel_tol_in = st.number_input("Parallel Tolerance (deg)", value=1.0, min_value=0.0, step=0.1, help="Angle alignment tolerance.")
    endpoint_tol_in = st.number_input("Endpoint Tolerance (mm)", value=20, min_value=0, help="Tolerance for connecting lines at endpoints.")

with st.sidebar.expander("📝 Dimension Styling", expanded=False):
    perp_dim_offset_in = st.number_input("Perpendicular Dim Offset", value=350, step=50)
    spacing_text_tmpl_in = st.text_input("Spacing Text Template", value="T8@200C/C")

# Visual preview setting
show_preview = st.sidebar.checkbox("Generate visual layout preview (takes a few seconds)", value=True)

params = {
    "TARGET_LAYER": target_layer_in,
    "GENERATED_LAYER": generated_layer_in,
    "BEHIND_MIN_DISTANCE": behind_min_in,
    "BEHIND_MAX_DISTANCE": behind_max_in,
    "FRONT_MIN_DISTANCE": front_min_in,
    "RATIO": ratio_in,
    "WALL_SIZE_TOLERANCE_PERCENT": wall_size_tol_in / 100.0,
    "PARALLEL_TOLERANCE": parallel_tol_in,
    "ENDPOINT_TOLERANCE": endpoint_tol_in,
    "PERP_DIM_OFFSET": perp_dim_offset_in,
    "SPACING_TEXT_TEMPLATE": spacing_text_tmpl_in
}

uploaded_file = st.file_uploader("Upload DXF File", type=["dxf"])

if uploaded_file is not None:
    st.success("File uploaded successfully!")
    
    # Save the file to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as temp_in:
        temp_in.write(uploaded_file.getvalue())
        temp_in_path = temp_in.name
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Process DXF file"):
            with st.spinner("Processing DXF features..."):
                # Read file
                try:
                    doc = ezdxf.readfile(temp_in_path)
                except ezdxf.DXFError as e:
                    try:
                        doc = ezdxf.readfile(temp_in_path, ignore_missing_linetypes=True)
                    except Exception as ex:
                        st.error(f"Failed to read DXF file: {ex}")
                        doc = None
                
                if doc is not None:
                    # Save original state bytes for rendering later
                    with open(temp_in_path, "rb") as f:
                        orig_bytes = f.read()
                    
                    # Capture printed logs
                    log_stream = io.StringIO()
                    with redirect_stdout(log_stream):
                        try:
                            processed_doc, stats = run_dxf_processing(doc, params)
                            success = True
                        except Exception as e:
                            success = False
                            st.error(f"Error during processing: {e}")
                    
                    if success:
                        logs = log_stream.getvalue()
                        st.session_state["logs"] = logs
                        st.session_state["stats"] = stats
                        st.session_state["orig_bytes"] = orig_bytes
                        
                        # Save the output doc to a temp file
                        temp_out_path = temp_in_path.replace(".dxf", "_processed.dxf")
                        processed_doc.saveas(temp_out_path)
                        with open(temp_out_path, "rb") as f:
                            processed_bytes = f.read()
                        
                        st.session_state["processed_bytes"] = processed_bytes
                        st.session_state["processed_filename"] = uploaded_file.name.replace(".dxf", "_processed.dxf")
                        
                        # Remove temp files
                        try:
                            os.remove(temp_out_path)
                        except:
                            pass

    # Clean up input temp file
    try:
        os.remove(temp_in_path)
    except:
        pass

    # Render results if available in session_state
    if "stats" in st.session_state and "processed_bytes" in st.session_state:
        stats = st.session_state["stats"]
        
        # Display Stats Cards
        st.write("### 📊 Processing Statistics")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["total_beams"]}</div><div class="metric-label">Total Beams</div></div>', unsafe_allow_html=True)
        with m_col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["total_perps"]}</div><div class="metric-label">Perpendiculars Drawn</div></div>', unsafe_allow_html=True)
        with m_col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["bylayer_count"]}</div><div class="metric-label">Processed Walls</div></div>', unsafe_allow_html=True)
        with m_col4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["hidden_count"]}</div><div class="metric-label">Processed Hidden Lines</div></div>', unsafe_allow_html=True)
        with m_col5:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["skipped_count"]}</div><div class="metric-label">Skipped Beams</div></div>', unsafe_allow_html=True)
        
        # Download button
        st.write("---")
        st.download_button(
            label="💾 Download Processed DXF File",
            data=st.session_state["processed_bytes"],
            file_name=st.session_state["processed_filename"],
            mime="application/dxf",
            key="download-dxf"
        )
        
        # Previews and Logs tabs
        tab1, tab2 = st.tabs(["🎨 Drawing Previews", "📋 Execution Logs"])
        
        with tab1:
            if show_preview:
                st.write("### 🖼️ Visual Drawing Previews")
                p_col1, p_col2 = st.columns(2)
                
                with p_col1:
                    st.write("**Original Drawing**")
                    with st.spinner("Rendering original layout..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as temp_orig:
                            temp_orig.write(st.session_state["orig_bytes"])
                            temp_orig_path = temp_orig.name
                        
                        try:
                            orig_doc = ezdxf.readfile(temp_orig_path)
                            orig_fig = render_dxf_modelspace(orig_doc)
                            if orig_fig:
                                st.pyplot(orig_fig)
                                plt.close(orig_fig)
                        except Exception as render_ex:
                            st.warning(f"Could not render original file preview: {render_ex}")
                        finally:
                            try:
                                os.remove(temp_orig_path)
                            except:
                                pass
                
                with p_col2:
                    st.write("**Processed Drawing (with Perpendiculars)**")
                    with st.spinner("Rendering processed layout..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as temp_proc:
                            temp_proc.write(st.session_state["processed_bytes"])
                            temp_proc_path = temp_proc.name
                        
                        try:
                            proc_doc = ezdxf.readfile(temp_proc_path)
                            proc_fig = render_dxf_modelspace(proc_doc)
                            if proc_fig:
                                st.pyplot(proc_fig)
                                plt.close(proc_fig)
                        except Exception as render_ex:
                            st.warning(f"Could not render processed file preview: {render_ex}")
                        finally:
                            try:
                                os.remove(temp_proc_path)
                            except:
                                pass
            else:
                st.info("Layout previews are disabled in the sidebar configuration.")
                
        with tab2:
            st.text_area("Console output", value=st.session_state["logs"], height=300, disabled=True)
