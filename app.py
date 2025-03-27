import streamlit as st
import plotly.express as px
import json
import os
from youtube_search import YoutubeSearch
from dotenv import load_dotenv
from groq import Groq  # Make sure to install with: pip install groq

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Career Roadmap Generator",
    page_icon="🚀",
    layout="wide"
)

# Initialize Groq client
def initialize_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in environment variables")
        st.stop()
    return Groq(api_key=api_key)

client = initialize_groq()

def generate_roadmap(current_status, target_role, experience):
    prompt = f"""
    Create a detailed JSON roadmap for transitioning from:
    {current_status}
    To: {target_role}
    With {experience} years experience.

    Return ONLY valid JSON with this exact structure:
    {{
        "roadmap_name": "Roadmap for {target_role}",
        "gap_analysis": "analysis text here",
        "timeline": [
            {{
                "phase": "Phase 1 (0-3)",
                "focus_areas": ["area1", "area2"],
                "milestones": ["milestone1", "milestone2"],
                "tasks": ["task1", "task2"]
            }}
        ],
        "estimated_time": "3-6 months"
    }}
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        response = chat_completion.choices[0].message.content
        roadmap = json.loads(response)
        return roadmap
        
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

def plot_timeline(roadmap_data):
    if not roadmap_data:
        return
    
    # Prepare data for Gantt chart
    gantt_data = []
    for phase in roadmap_data.get("timeline", []):
        phase_name = phase["phase"]
        
        # Extract time range (e.g., "0-3" -> 0, 3)
        try:
            time_range = phase_name.split("(")[-1].split(")")[0]
            start, end = map(int, time_range.split("-")[:2])
        except (ValueError, IndexError, AttributeError):
            start, end = 0, 3  # Default values
            
        for area in phase["focus_areas"]:
            gantt_data.append({
                "Task": area,
                "Phase": phase_name,
                "Start": start,
                "Finish": end,
                "Milestones": "\n".join(phase["milestones"])
            })
    
    if not gantt_data:
        return
    
    fig = px.timeline(
        gantt_data,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Phase",
        title="Roadmap Timeline",
        hover_name="Task",
        hover_data=["Milestones"]
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=500, 
        xaxis_title="Months",
        xaxis=dict(tickvals=list(range(0, 13)), 
                  ticktext=[f"{m} month(s)" for m in range(0, 13)])
    )
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Career Path Planner)")
    
    # Input Section
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            current_status = st.text_area("Current Skills/Experience", height=200)
        with col2:
            target_role = st.text_input("Target Role")
            experience = st.slider("Years of Experience", 0, 30, 2)
        
        if st.button("Generate Roadmap", type="primary"):
            if current_status and target_role:
                with st.spinner("Creating personalized roadmap..."):
                    roadmap = generate_roadmap(current_status, target_role, experience)
                    if roadmap:
                        st.session_state.roadmap = roadmap
            else:
                st.warning("Please fill all fields")

    # Display Results
    if "roadmap" in st.session_state:
        tab1, tab2, tab3 = st.tabs(["Roadmap", "Projects", "Resources"])
        
        with tab1:
            st.subheader(st.session_state.roadmap["roadmap_name"])
            st.markdown(f"**Gap Analysis:** {st.session_state.roadmap['gap_analysis']}")
            plot_timeline(st.session_state.roadmap)
            
            with st.expander("Detailed Timeline"):
                for phase in st.session_state.roadmap["timeline"]:
                    st.markdown(f"### {phase['phase']}")
                    st.markdown("**Focus Areas:** " + ", ".join(phase["focus_areas"]))
                    st.markdown("**Tasks:**")
                    for task in phase["tasks"]:
                        st.markdown(f"- {task}")
        
        with tab2:
            st.subheader("Recommended Projects")
            try:
                projects_prompt = f"Suggest 3 hands-on projects for {target_role} considering: {current_status}"
                projects_response = client.chat.completions.create(
                    messages=[{"role": "user", "content": projects_prompt}],
                    model="llama-3.3-70b-versatile"
                )
                st.markdown(projects_response.choices[0].message.content)
            except Exception as e:
                st.error(f"Failed to generate projects: {str(e)}")
        
        with tab3:
            st.subheader("Learning Resources")
            try:
                results = YoutubeSearch(f"{target_role} learning resources", max_results=5).to_dict()
                for i, video in enumerate(results, 1):
                    st.markdown(f"{i}. [{video['title']}](https://youtube.com{video['url_suffix']})")
            except Exception as e:
                st.error(f"YouTube search failed: {str(e)}")

if __name__ == "__main__":
    main()