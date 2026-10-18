"""Check source video and replacement voice before submitting a lipsync job.

Usage: python check_lipsync_inputs.py source.mp4 voice.wav
Requires ffprobe and ffmpeg on PATH. Does not upload files or call a service.
"""
import argparse
import json
import subprocess
import sys


def inspect(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path],
        check=True, capture_output=True, text=True, encoding='utf-8',
    )
    return json.loads(result.stdout)


def check(source, voice):
    video_info, voice_info = inspect(source), inspect(voice)
    video_types = {s['codec_type'] for s in video_info.get('streams', [])}
    voice_types = {s['codec_type'] for s in voice_info.get('streams', [])}
    errors = []
    if 'video' not in video_types:
        errors.append('Source has no video stream.')
    if 'audio' not in video_types:
        errors.append('Source has no original audio stream; the lipsync service may reject it.')
    if 'audio' not in voice_types:
        errors.append('Replacement voice has no audio stream.')
    for label, info in [('source', video_info), ('voice', voice_info)]:
        if float(info.get('format', {}).get('duration', 0)) <= 0:
            errors.append(f'{label} duration must be positive.')
    if not errors:
        for path in [source, voice]:
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', path, '-f', 'null', '-'],
                           check=True, capture_output=True)
    return {'ok': not errors, 'errors': errors,
            'source_duration': video_info.get('format', {}).get('duration'),
            'voice_duration': voice_info.get('format', {}).get('duration')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('voice')
    args = parser.parse_args()
    try:
        report = check(args.source, args.voice)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(json.dumps({'ok': False, 'errors': [str(error)]}))
        sys.exit(2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['ok'] else 1)
