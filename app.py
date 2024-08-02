import streamlit as st
import time
import assemblyai as aai
import pandas as pd
import plotly.express as px
from pydub import AudioSegment
import tempfile
import os

aai.settings.api_key = st.text_input("AssemblyAI API Key: ", value=st.secrets["AAI_API_KEY"], type="password")
transcriber = aai.Transcriber()

@st.cache_data
def get_audio_duration(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
        tmp_file.write(file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        audio = AudioSegment.from_file(tmp_file_path)
        duration = len(audio) / 1000.0  
    except Exception as e:
        st.error(f"Error reading audio file: {e}")
        duration = None
    finally:
        os.unlink(tmp_file_path)

    return duration

def transcribe_file(file, language_detection=True, language_code=None):
    if language_detection==True:
            
            config = aai.TranscriptionConfig(
            language_detection=language_detection,
        )
    else:

        config = aai.TranscriptionConfig(
            language_code=language_code
        )
    
    start_time = time.time()
    transcript = transcriber.transcribe(file, config)
    end_time = time.time()
    
    if transcript.status == aai.TranscriptStatus.error:
        st.error(f"Transcription failed: {transcript.error}")
        return None, None
    
    return transcript, end_time - start_time

def process_file(file, provided_language_code):
    duration = get_audio_duration(file)
    if duration is None:
        return None
    
    upload_url = transcriber.upload_file(file)

    transcript_with, time_with = transcribe_file(upload_url, language_detection=True)
    if transcript_with is None:
        return None

    transcript_without, time_without = transcribe_file(upload_url, language_detection=False, language_code=provided_language_code)
    if transcript_without is None:
        return None

    time_difference = time_with - time_without
    percentage_difference = (time_difference / duration) * 100

    return {
        "File": file.name,
        "Detected Language": transcript_with.json_response["language_code"],
        "Actual Language": provided_language_code,
        "Time with ALD (seconds)": time_with,
        "Time without ALD (seconds)": time_without,
        "Processing Time As % Of File Duration": percentage_difference,
        "File Length (seconds)": duration,
    }

st.title("ALD Processing Time Tester")

uploaded_files = st.file_uploader("Upload audio files", accept_multiple_files=True, type=['mp3', 'wav', 'mp4', 'm4a'])

if uploaded_files:
    file_language_codes = {}
    for file in uploaded_files:
        language_code = st.text_input(f"Enter actual language code for {file.name}", "")
        file_language_codes[file.name] = language_code

    if st.button("Test"):
        results = []
        for file in uploaded_files:
            with st.spinner(f'Processing {file.name}...'):
                result = process_file(file, file_language_codes[file.name])
                if result:
                    results.append(result)

        if results:
            st.divider()
            st.title("Results: ")
            df = pd.DataFrame(results)
            st.write(df)

            mean_val = df["Processing Time As % Of File Duration"].mean()
            std_val = df["Processing Time As % Of File Duration"].std()

            fig = px.scatter(df, x="File Length (seconds)", y="Processing Time As % Of File Duration", 
                            color="Detected Language", hover_data=["File", "Actual Language"],
                            title="Processing Time For ALD As % Of File Duration")

            fig.update_layout(yaxis_title="Processing Time As % Of File Duration")

            fig.add_shape(
                type="line",
                x0=df["File Length (seconds)"].min(), x1=df["File Length (seconds)"].max(),
                y0=mean_val + 1*std_val, y1=mean_val + 1*std_val,
                line=dict(color="Red", width=2, dash="dashdot"),
                name="Mean + 3 Std Dev"
            )
            fig.add_shape(
                type="line",
                x0=df["File Length (seconds)"].min(), x1=df["File Length (seconds)"].max(),
                y0=mean_val - 1*std_val, y1=mean_val - 1*std_val,
                line=dict(color="Red", width=2, dash="dashdot"),
                name="Mean - 3 Std Dev"
            )

            st.plotly_chart(fig)
        else:
            st.warning("Results error")
else:
    st.write("Upload files.")
