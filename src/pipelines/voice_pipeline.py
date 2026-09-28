import io
import numpy as np
import streamlit as st

# Safe import of optional voice recognition dependencies
try:
    import librosa
    from resemblyzer import VoiceEncoder, preprocess_wav
    VOICE_RECOGNITION_AVAILABLE = True
    VOICE_IMPORT_ERROR = None
except Exception as err:
    VOICE_RECOGNITION_AVAILABLE = False
    VOICE_IMPORT_ERROR = str(err)
    librosa = None
    VoiceEncoder = None
    preprocess_wav = None


@st.cache_resource
def load_voice_encoder():
    if not VOICE_RECOGNITION_AVAILABLE:
        return None
    try:
        return VoiceEncoder()
    except Exception as e:
        st.warning(f"Voice encoder initialization error: {e}")
        return None


def get_voice_embedding(audio_bytes):
    if not audio_bytes:
        return None

    if not VOICE_RECOGNITION_AVAILABLE:
        st.warning(f"Voice recognition is not supported in this runtime environment: {VOICE_IMPORT_ERROR}")
        return None

    try:
        encoder = load_voice_encoder()
        if not encoder:
            return None

        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        wav = preprocess_wav(audio)
        embedding = encoder.embed_utterance(wav)
        return embedding.tolist()
    except Exception as e:
        st.error(f'Voice recognition error: {e}')
        return None


def identify_speaker(new_embedding, candidates_dict, threshold=0.65):
    if new_embedding is None or not candidates_dict:
        return None, 0.0

    best_sid = None
    best_score = -1.0
    new_emb_np = np.array(new_embedding, dtype=np.float64)

    for sid, stored_embedding in candidates_dict.items():
        if stored_embedding:
            stored_emb_np = np.array(stored_embedding, dtype=np.float64)
            norm_product = np.linalg.norm(new_emb_np) * np.linalg.norm(stored_emb_np) + 1e-8
            similarity = float(np.dot(new_emb_np, stored_emb_np) / norm_product)
            if similarity > best_score:
                best_score = similarity
                best_sid = sid

    if best_score >= threshold:
        return best_sid, best_score

    return None, best_score


def process_bulk_audio(audio_bytes, candidates_dict, threshold=0.65):
    if not audio_bytes or not candidates_dict:
        return {}

    if not VOICE_RECOGNITION_AVAILABLE:
        st.warning(f"Voice recognition is not supported in this runtime environment: {VOICE_IMPORT_ERROR}")
        return {}

    try:
        encoder = load_voice_encoder()
        if not encoder:
            return {}

        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)
        segments = librosa.effects.split(audio, top_db=30)

        identified_results = {}

        for start, end in segments:
            if (end - start) < sr * 0.5:
                continue
            segment_audio = audio[start:end]
            wav = preprocess_wav(segment_audio)
            embedding = encoder.embed_utterance(wav)

            sid, score = identify_speaker(embedding, candidates_dict, threshold)

            if sid:
                score_rounded = round(float(score), 3)
                if sid not in identified_results or score_rounded > identified_results[sid]:
                    identified_results[sid] = score_rounded

        return identified_results
    except Exception as e:
        st.error(f'Bulk audio process error: {e}')
        return {}
