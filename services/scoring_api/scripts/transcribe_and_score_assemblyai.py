#!/usr/bin/env python3
"""
Upload an audio file to AssemblyAI, poll for transcription, then run local PTE scoring.

Usage:
  python transcribe_and_score_assemblyai.py /path/to/audio.m4a

Environment:
  Set `ASSEMBLYAI_API_KEY` in the environment or in `services/scoring_api/.env`.

This script will print a JSON object with keys: `transcript` and `scores`.
"""
import json
import os
import sys
import time
from pathlib import Path

try:
    # optional: load from .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / '.env')
except Exception:
    pass

import requests

ROOT = Path(__file__).resolve().parents[1]


def upload_file(api_key: str, filepath: Path) -> str:
    url = 'https://api.assemblyai.com/v2/upload'
    headers = {'authorization': api_key}
    with open(filepath, 'rb') as f:
        # stream upload in chunks
        def gen():
            while True:
                chunk = f.read(524288)
                if not chunk:
                    break
                yield chunk
        resp = requests.post(url, headers=headers, data=gen())
    resp.raise_for_status()
    return resp.json().get('upload_url')


def create_transcript(api_key: str, audio_url: str) -> str:
    url = 'https://api.assemblyai.com/v2/transcript'
    headers = {'authorization': api_key, 'content-type': 'application/json'}
    payload = {'audio_url': audio_url}
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json().get('id')


def poll_transcript(api_key: str, transcript_id: str, timeout: int = 300) -> dict:
    url = f'https://api.assemblyai.com/v2/transcript/{transcript_id}'
    headers = {'authorization': api_key}
    start = time.time()
    while True:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        status = data.get('status')
        if status == 'completed':
            return data
        if status == 'error':
            raise RuntimeError('Transcription error: ' + json.dumps(data))
        if time.time() - start > timeout:
            raise TimeoutError('Transcription timed out')
        time.sleep(2)


def main():
    audio_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'tmp' / 'test_audio.m4a'
    if not audio_path.exists():
        print(f'Audio file not found: {audio_path}', file=sys.stderr)
        sys.exit(2)

    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    if not api_key:
        print('Set ASSEMBLYAI_API_KEY in environment or in services/scoring_api/.env', file=sys.stderr)
        sys.exit(2)

    print('Uploading audio to AssemblyAI...', file=sys.stderr)
    upload_url = upload_file(api_key, audio_path)
    print('Upload URL:', upload_url, file=sys.stderr)

    print('Creating transcription job...', file=sys.stderr)
    transcript_id = create_transcript(api_key, upload_url)
    print('Transcript ID:', transcript_id, file=sys.stderr)

    print('Waiting for transcription to complete...', file=sys.stderr)
    result = poll_transcript(api_key, transcript_id)
    transcript_text = result.get('text', '')

    # Import scoring function from project
    try:
        from services.scoring_api.app.core.pte_nlp_scorer import compute_pte_scores
    except Exception:
        # fallback import path
        from app.core.pte_nlp_scorer import compute_pte_scores

    scores = compute_pte_scores(transcript_text)

    out = {'transcript': transcript_text, 'scores': scores, 'assemblyai_result': result}
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
