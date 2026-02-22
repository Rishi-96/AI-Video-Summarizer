import sys
sys.path.append('D:\\video-summarizer\\backend')

from app.models.whisper_fixed import FixedWhisperTranscriber

print('🔄 Initializing transcriber...')
transcriber = FixedWhisperTranscriber('tiny')

print('✅ Transcriber initialized!')
print('📝 Testing mock transcription...')
result = transcriber.transcribe_file('test.mp4')
print(f'   Text: {result[\"text\"][:100]}...')
print(f'   Language: {result[\"language\"]}')
print(f'   Segments: {len(result[\"segments\"])}')

print('\n✅ Test passed! The fixed transcriber is working.')
