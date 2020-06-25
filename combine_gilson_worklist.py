import os
import sys
import re
import datetime

shared_drive = 'N:/tecan/SourceData/SecondStage/'
#shared_drive = '/Users/trinhsk/Documents/pythonScripts/'

list_file_names = []
int_start_sample_pos = 0
int_start_plt_loc = 0

def readFiles(rack_code):
    global list_file_names
    file_name = ''
    for fi in os.listdir(shared_drive):
        if fi.endswith('.tsl') and 'and' not in fi:
            if rack_code in fi:
                try:
                    file_mtime = os.stat(os.path.join(shared_drive,fi)).st_mtime
                    if datetime.datetime.fromtimestamp(file_mtime) < datetime.datetime.today():
                        file_name = os.path.join(shared_drive,fi)
                        list_file_names.append(fi)
                        with open(file_name, 'r') as f:
                            file_content = f.readlines()
                except ValueError:
                    pass
    return file_content


def replace_tsl_values(file2): 
    enum_ = 1
    new_tsl = []
    global int_start_plt_loc
    global int_start_sample_pos

    for i,line in enumerate(file2[5:]):
        if 'FLUSH' in line or 'STD' in line or 'SHUTDOWN' in line:
            new_tsl.append(line)
        else:
            try:
                plt_loc = re.search('\tP\d{1,2}S', line).group(0)
                if int(plt_loc[2:len(plt_loc)-1]) > 9:
                    padding = ""
                else:
                    padding = "0"
                
                new_tsl.append(line.replace(plt_loc, f'\tP{padding}{str(int_start_plt_loc)}S'))

                sample_num = re.search('\t(?![0])\d{1,2}\t', line).group(0)
                new_tsl[i] = new_tsl[i].replace(sample_num, f'\t{str(int_start_sample_pos)}\t')
                int_start_sample_pos += 1
                if enum_ % 4 == 0:
                    int_start_plt_loc += 1
                enum_ += 1
            except AttributeError as e:
                pass
    return new_tsl

def init_start_nums(file1):
    global int_start_sample_pos
    global int_start_plt_loc
    str_start_sample_pos = re.search('\t(?![0])\d{1,2}\t', file1[len(file1)-6]).group(0)
    int_start_sample_pos = int(str_start_sample_pos) + 1
    str_start_plt_loc = re.search('\tP\d{1,2}S', file1[len(file1)-6]).group(0)
    int_start_plt_loc = int(str_start_plt_loc[2:len(str_start_plt_loc)-1]) + 1


if __name__ == "__main__":
    if int(sys.argv[1]) and int(sys.argv[2]) and len(sys.argv[1]) == 11 and len(sys.argv[2]) == 11:
        input_file_name1 = sys.argv[1]
        input_file_name2 = sys.argv[2]
        list_of_racks = sorted([input_file_name1] + [input_file_name2])
        file1 = readFiles(list_of_racks[0])
        file2 = readFiles(list_of_racks[1])
        init_start_nums(file1)
        top_tsl = file1[:len(file1)-3]
        bottom_tsl = replace_tsl_values(file2)
        new_tsl = top_tsl + bottom_tsl
        date_now = datetime.datetime.today().strftime("%d%m%Y") 
        trunc_filename1 = list_file_names[0].split('_')[2].replace('.tsl','')
        trunc_filename2 = list_file_names[1].split('_')[2].replace('.tsl','')
        with open(f"{shared_drive}/{date_now}_secStg_{trunc_filename1}_and_{trunc_filename2}.tsl", 'w') as f:
            for line in new_tsl:
                f.write(line)
    else:
            print('enter two valid values')
            
