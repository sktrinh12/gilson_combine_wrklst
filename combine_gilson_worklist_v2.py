import os
import sys
import re
import datetime
import platform

if platform.system() == "Windows":
    shared_drive = 'N:\\tecan\\SourceData\\SecondStage\\'
    fp_delim = '\\'
else:
    shared_drive = '/Volumes/npsg/tecan/SourceData/SecondStage/'
    fp_delim = '/'

sample_list_dir = 'Sample List_tsl'
list_file_names = []


def readFiles(rack_code):
    global list_file_names
    file_content = None
    file_path_to_file = f"{shared_drive}{sample_list_dir}"
    if os.path.exists(file_path_to_file):
        for fi in os.listdir(file_path_to_file):
            if fi.endswith('.tsl') and 'secStg' in fi:
                if rack_code in fi:
                    try:
                        file_mtime = os.stat(os.path.join(
                            file_path_to_file, fi)).st_mtime
                        if datetime.datetime.fromtimestamp(file_mtime) < datetime.datetime.today():
                            file_name = os.path.join(file_path_to_file, fi)
                            list_file_names.append(fi)
                            with open(file_name, 'r') as f:
                                file_content = f.readlines()
                            break
                    except ValueError:
                        pass
    else:
        print(f"Can't access the share drive! - {shared_drive}")
        return None
    return file_content


def check_file_content(file_content):
    if not file_content:
        print(f"Couldn't find file or file was empty!")
        return False
    return True


def replace_tsl_values(file_, int_start_sample_num):
    new_tsl = {}
    for i, line in enumerate(file_[5:]):
        if 'FLUSH' in line or 'STD' in line or 'SHUTDOWN' in line:
            new_tsl[i] = line
        else:
            try:
                int_start_sample_num += 1
                sample_num = re.search('\t(?![0])\d{1,2}\t', line).group(0)
                new_tsl[i] = line.replace(
                    sample_num, f'\t{int_start_sample_num}\t')
            except AttributeError as e:
                print(e)
    return [v for v in new_tsl.values()]


def replace_tsl_values_2(tsl, plt_start):
    new_tsl = tsl.copy()
    line_cnt = 1
    plt_start += 1
    for i, line in enumerate(new_tsl):
        if 'FLUSH' in line or 'STD' in line or 'SHUTDOWN' in line:
            pass
        else:
            well_loc = 4 if line_cnt % 4 == 0 else line_cnt % 4

            if plt_start > 9:
                padding = ""
            else:
                padding = "0"
            str_plt_well = re.search('\tP\d{2}S\d{2}\n', line).group(0)
            new_tsl[i] = line.replace(
                str_plt_well, f"\tP{padding}{plt_start}S0{well_loc}\n")
            if line_cnt % 4 == 0:
                plt_start += 1
            line_cnt += 1
    return new_tsl


def grab_sam_plt_nums(file1):
    for i in reversed(range(len(file1))):
        # if do not see the 0 in the sample well pos (it's a sample not std/flush)
        if not re.search('\t0.?\n', file1[i]):
            str_start_sample_pos = re.search(
                '\t(?![0])\d{1,2}\t', file1[i]).group(0)
            str_start_plt_loc = re.search('\tP\d{1,2}S', file1[i]).group(0)
            break
    int_start_sample_pos = int(str_start_sample_pos)
    int_start_plt_loc = int(
        str_start_plt_loc[2:len(str_start_plt_loc)-1])  # rid of 0
    if int_start_sample_pos % 4 != 0:  # if not a mutliple of 4 samples need to add buffer for bottom tsl
        int_start_sample_pos = int_start_sample_pos + \
            (int_start_sample_pos % 4)
    return int_start_sample_pos, int_start_plt_loc


def extract_brooks_bc(tsl_file):
    try:
        for i in reversed(range(len(tsl_file))):
            # if do not see the 0 in the sample well pos (it's a sample not std/flush)
            if not re.search('\t0.?\n', tsl_file[i]):
                return re.search('(...\t)(\d{3,}\s)', tsl_file[i]).group(2).strip()
    except Exception as e:
        return 'NA'


if __name__ == "__main__":
    if len(sys.argv[1]) == 10 and len(sys.argv[2]) == 10:
        input_file_name1 = sys.argv[1]
        input_file_name2 = sys.argv[2]
        list_of_racks = sorted([input_file_name1] + [input_file_name2])
        file1 = readFiles(list_of_racks[0])
        file2 = readFiles(list_of_racks[1])
        if check_file_content(file2) and check_file_content(file1):
            int_start_sample_num, int_start_plt_loc = grab_sam_plt_nums(
                file1)  # grab the sample pos and plate loc
            top_tsl = file1[:len(file1)-3]
            bottom_tsl = replace_tsl_values(file2, int_start_sample_num)
            bottom_tsl = replace_tsl_values_2(bottom_tsl, int_start_plt_loc)
            new_tsl = top_tsl + bottom_tsl  # combine the two worklists
            project_id = input_file_name1[:8]
            file_1_suffix = list_of_racks[0][8:]
            file_2_suffix = list_of_racks[1][8:]
            bbc1 = extract_brooks_bc(file1)
            bbc2 = extract_brooks_bc(file2)
            with open(f"{shared_drive}Sample List_Combined_tmp{fp_delim}{project_id}_{file_1_suffix}_{file_2_suffix}_{bbc1}_{bbc2}.tsl", 'w') as f:
                for line in new_tsl:
                    f.write(line)

            print('successfully combined worklists!')
    else:
        print('enter two valid values')
