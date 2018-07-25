
import subprocess

result_array = []

iterate = ['4']
thresh = ['30']
video_path = "birds_052117_205059.mp4"


for i in range(len(iterate)):
    for t in range(len(thresh)):
        result = subprocess.run(['python', 'obj_detec_test_v2.py', thresh[t], iterate[i], video_path], stdout=subprocess.PIPE).stdout.decode('utf-8')
        print("Iterate: {} Threshold: {} Count: {}".format(iterate[i], thresh[t],result))
        with open("count_{}.txt".format(video_path), "a") as myfile:
            myfile.write("Iterate:{} Thresh:{} Count:{}\n".format(iterate[i], thresh[t], result))
        result_array.append(result)
