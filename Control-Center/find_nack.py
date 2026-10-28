import glob

file_list = glob.glob("data\\float_profile_data_2025_06_06*")
print (file_list)
exit

for file_name in file_list:
    print(file_name)
    f = open(file_name)
    missing = []
    prev_ts = 0
    
    while True:
        line = f.readline()
        if (not line):
            break
        tokens = line.split(" ")
        ts = int(tokens[1])
        if (prev_ts > 0 and ts > prev_ts + 2):
            missing.append([prev_ts, ts])
        prev_ts = ts
        
    f.close()
    print("NACK count: ", len(missing))
    print(missing)