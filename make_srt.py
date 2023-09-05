import os
import json
import io
from google.cloud import speech_v1
from google.cloud import speech
import subprocess
from pydub.utils import mediainfo
import subprocess
import math
import datetime
import srt
import io

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=""


def long_running_recognize(channels, sample_rate):
    
    client = speech.SpeechClient()

    #use gcs if the file is big
    gcs_uri = "gs://{bucket}/{flac_format_file_name}"
    audio = speech.RecognitionAudio(uri=gcs_uri)

    config = {
        "language_code": "vi-VN",
        "sample_rate_hertz": int(sample_rate),
        "encoding": speech.RecognitionConfig.AudioEncoding.FLAC,
        "audio_channel_count": int(channels),
        "enable_word_time_offsets": True,
        "model": "latest_long",
        "enable_automatic_punctuation":True
    }

    operation = client.long_running_recognize(config=config, audio=audio)

    print(u"Waiting for operation to complete...")
    response = operation.result()
    return response

def subtitle_generation(speech_to_text_response, bin_size=3):
    """We define a bin of time period to display the words in sync with audio. 
    Here, bin_size = 3 means each bin is of 3 secs. 
    All the words in the interval of 3 secs in result will be grouped togather."""
    transcriptions = []
    index = 0
    response = speech_to_text_response
    for result in response.results:
        try:
            if result.alternatives[0].words[0].start_time.seconds:
                # bin start -> for first word of result
                start_sec = result.alternatives[0].words[0].start_time.seconds 
                start_microsec = result.alternatives[0].words[0].start_time.microseconds 
            else:
                # bin start -> For First word of response
                start_sec = 0
                start_microsec = 0 
            end_sec = start_sec + bin_size # bin end sec
            
            # for last word of result
            last_word_end_sec = result.alternatives[0].words[-1].end_time.seconds
            last_word_end_microsec = result.alternatives[0].words[-1].end_time.microseconds 
            
            # bin transcript
            transcript = result.alternatives[0].words[0].word
            
            index += 1 # subtitle index

            for i in range(len(result.alternatives[0].words) - 1):
                try:
                    word = result.alternatives[0].words[i + 1].word
                    word_start_sec = result.alternatives[0].words[i + 1].start_time.seconds
                    word_start_microsec = result.alternatives[0].words[i + 1].start_time.microseconds  # 0.001 to convert nana -> micro
                    word_end_sec = result.alternatives[0].words[i + 1].end_time.seconds
                    word_end_microsec = result.alternatives[0].words[i + 1].end_time.microseconds 

                    if word_end_sec < end_sec:
                        transcript = transcript + " " + word
                    else:
                        previous_word_end_sec = result.alternatives[0].words[i].end_time.seconds
                        previous_word_end_microsec = result.alternatives[0].words[i].end_time.microseconds 
                        
                        # append bin transcript
                        transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, previous_word_end_sec, previous_word_end_microsec), transcript))
                        
                        # reset bin parameters
                        start_sec = word_start_sec
                        start_microsec = word_start_microsec
                        end_sec = start_sec + bin_size
                        transcript = result.alternatives[0].words[i + 1].word
                        
                        index += 1
                except IndexError:
                    pass
            # append transcript of last transcript in bin
            transcriptions.append(srt.Subtitle(index, datetime.timedelta(0, start_sec, start_microsec), datetime.timedelta(0, last_word_end_sec, last_word_end_microsec), transcript))
            index += 1
        except IndexError:
            pass
    
    # turn transcription list into subtitles
    subtitles = srt.compose(transcriptions)
    return subtitles


response = long_running_recognize(1, 48000)
subtitles = subtitle_generation(response)
with open("subtitles.srt", "w") as f:
    f.write(subtitles)


#https://brunch.co.kr/@stopyeonee/16
#https://blog.searce.com/generate-srt-file-subtitles-using-google-clouds-speech-to-text-api-402b2f1da3bd
#