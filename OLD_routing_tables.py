import matplotlib.pyplot as plt
import pandas as pd

__author__ = 'christina'

FILENAME = 'ncu 8_rt-tbl-1.txt'
COMMANDS = {
    'load list': '3',
    'rt-tbl': 'm',
}

LIST_NUM = 'list_id'
LOW_ADDR = 'low_addr'
MY_ADDR = 'MY_addr'
COUNT = 'updated count'
H1 = 'hop 1'
H2 = 'hop 2'
H3 = 'hop 3'
H4 = 'hop 4'
H5 = 'hop 5'
H6 = 'hop 6'
H7 = 'hop 7'
H8 = 'hop 8'
HOP_LIST = [H1, H2, H3, H4, H5, H6, H7, H8]
SN = 's/n'
NAME = 'Name'
F_BIT = 'Feature bit'
OLD_COUNT = 'old count'
MAX_PATH_LENGTH = 8
COLOR_WHEEL = ['black', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'magenta', 'gray']
COORDINATOR_DUMMY_VALUE = -1  # when COUNT == 0, replaces the initial '0000' to represent the coordinator
PHANTOM_DUMMY_VALUE = -2  # replaces network ids that no longer exist
FILLER_DUMMY_VALUE = -10  # replaces '0000' for graphing entire routing table


def get_routing_table_dataframe(filename=FILENAME):
    f = open(filename, 'r')
    cleaned_response = parse_command_response(f, 'rt-tbl')
    f.close()
    routing_table = pd.DataFrame(cleaned_response, columns=[LIST_NUM, LOW_ADDR, MY_ADDR, COUNT, H1, H2, H3, H4, H5, H6, H7, H8])
    old_hops = count_old_hops(routing_table)
    routing_table[OLD_COUNT] = old_hops
    return routing_table


def get_load_list_dataframe(filename=FILENAME):
    f = open(filename, 'r')
    cleaned_response = parse_command_response(f, 'load list')
    f.close()
    return pd.DataFrame(cleaned_response, columns=[LOW_ADDR, SN, NAME, F_BIT])


def get_mapping_file_dataframe(filename=FILENAME):
    # creates dataframe from a tab-delimited file
    mapping_file_df = pd.read_csv(filename, sep='\t', names=[NAME, SN, F_BIT, LOW_ADDR])
    mapping_file_df[LOW_ADDR] = mapping_file_df[LOW_ADDR].apply(lambda x: x.lower())
    return mapping_file_df


def parse_command_response(f, command):
    cleaned_response = []
    low_addr = []
    line_start = 'Resp: ' + COMMANDS[command] + ','
    for line in f:
        if line_start in line and line.count(',') > 2 and 'fffe' not in line:
            cleaned_line = line.lstrip(line_start).strip().lower().split(',')
            cleaned_line[0] = int(cleaned_line[0])  # convert list id from string to int to allow for operations
            cleaned_line[3] = int(cleaned_line[3])  # convert zigbee count from string to int to allow for operations
            if cleaned_line[1] in low_addr:
                cleaned_response[low_addr.index(cleaned_line[1])] = cleaned_line
                # print cleaned_line[1]
            else:
                low_addr.append(cleaned_line[1])
                cleaned_response.append(cleaned_line)
            # print str(cleaned_line[0]) + ', ' + cleaned_line[1]
    return cleaned_response


def map_my_addr_to_num(sorted_by_name):
    my_address_map = dict(zip(sorted_by_name.loc[:, MY_ADDR], sorted_by_name.index))
    my_address_map['0000'] = FILLER_DUMMY_VALUE  # '0000' can either mean the coordinator if COUNT == 0 or 'not used' if COUNT > 0
    return my_address_map


def count_old_hops(rt_tbl_df):
    source_table_only = rt_tbl_df.loc[:, [H1, H2, H3, H4, H5, H6, H7, H8]]
    return source_table_only.apply(lambda x: MAX_PATH_LENGTH - list(x).count('0000'), axis=1)


# def get_hops(hop_series, address_map):
#     # For the input Series (representing the i-th hop), this function converts an SPC's network id to its index value.
#     hop_list = []
#     phantom_list = []
#     for h in hop_series:
#         try:
#             hop_list.append(address_map[h])
#         except KeyError:
#             hop_list.append(PHANTOM_DUMMY_VALUE)  # need a bogus value so that the returned list has the correct dimension.
#             if h not in phantom_list:
#                 phantom_list.append(h)
#     print phantom_list
#     return hop_list


def separate_old_and_current_hops(sorted_df):
    address_map = map_my_addr_to_num(sorted_df)
    old_hops = sorted_df.copy()
    current_hops = sorted_df.copy()

    for i in range(1, MAX_PATH_LENGTH + 1):
        for j in sorted_df.index:  # for each SPC, compare the zigbee hop count to the hop iteration you are on
            if sorted_df.loc[j, HOP_LIST[i - 1]] != '0000':
                if sorted_df.loc[j, COUNT] >= i:
                    # send SPC to current hops bucket + put dummy filler value in old hops bucket
                    try:
                        current_hops.loc[j, HOP_LIST[i - 1]] = address_map[sorted_df.loc[j, HOP_LIST[i-1]]]
                    except KeyError:
                        current_hops.loc[j, HOP_LIST[i - 1]] = PHANTOM_DUMMY_VALUE
                    old_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                elif sorted_df.loc[j, COUNT] == 0:
                    # routes directly to coordinator
                    current_hops.loc[j, HOP_LIST[i - 1]] = COORDINATOR_DUMMY_VALUE
                    old_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                else:
                    # send SPC to old hops bucket + put dummy filler value in current hops bucket
                    try:
                        old_hops.loc[j, HOP_LIST[i - 1]] = address_map[sorted_df.loc[j, HOP_LIST[i - 1]]]
                    except KeyError:
                        old_hops.loc[j, HOP_LIST[i - 1]] = PHANTOM_DUMMY_VALUE
                    current_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
            else:
                current_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                old_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
    return old_hops, current_hops


def plot_source_route(current_df, old_df=None):
    plt.figure(figsize=(22, 22))
    plt.plot(current_df.index, current_df.index, 'k-')
    [plt.plot(current_df.index, current_df[HOP_LIST[i]],
              color=COLOR_WHEEL[i], marker='o', mec='None', markersize=10, linestyle='None')
     for i in range(0, MAX_PATH_LENGTH)]
    if old_df is not None:
        [plt.plot(old_df.index, old_df[HOP_LIST[i]], color='None', marker='o', mec='black', markersize=10,
                  linestyle='None')
         for i in range(0, MAX_PATH_LENGTH)]
    plt.xticks(current_df.index, current_df.loc[:, NAME], rotation=90, fontsize=8)
    plt.yticks([PHANTOM_DUMMY_VALUE, COORDINATOR_DUMMY_VALUE] + list(current_df.index),
               ['phantom', 'coordinator'] + list(current_df.loc[:, NAME]),
               fontsize=8)
    plt.grid(True, which='major', axis='both')
    plt.xlim(0, len(current_df.index))
    plt.ylim(PHANTOM_DUMMY_VALUE - 1, len(current_df.index))
    plt.legend(['self', H1, H2, H3, H4, H5, H6, H7, H8, 'invalid'], loc='center left', bbox_to_anchor=(1.0, 0.5))
    plt.title('Source Routing Paths')
    plt.xlabel('SPC')
    plt.ylabel('SPC in Route')


def plot_hops_frequency(df):
    plt.figure(figsize=(5, 5))
    zeros = pd.Series((MAX_PATH_LENGTH + 1) * [0])
    frequency = df[COUNT].value_counts(sort=False)/len(df[COUNT])
    plt.plot(frequency.add(zeros, fill_value=0), 'bo-')
    plt.ylim(0, 1.0)
    plt.xlabel('Number of Hops')
    plt.ylabel('Frequency')


def plot_num_valid_hops(sorted_df):
    plt.figure(figsize=(22, 8))
    plt.plot(sorted_df[COUNT], 'bo')
    plt.xticks(sorted_df.index, sorted_df.loc[:, NAME], rotation=90, fontsize=8)
    plt.ylim(0, 5)
    plt.xlabel('SPC')
    plt.ylabel('Number of valid hops on route')

rt_tbl_file = '88_32.txt'
print rt_tbl_file
mapping_file = '192.168.14.88.txt'

rt_tbl = get_routing_table_dataframe(rt_tbl_file)
# plot_hops_frequency(rt_tbl)
# plt.title(rt_tbl_file)

# spc_list = get_load_list_dataframe('ncu 8_load-list.txt')
spc_list = get_mapping_file_dataframe(mapping_file)
merged = pd.DataFrame.merge(spc_list, rt_tbl, on=LOW_ADDR).sort_values(by=NAME)
(old, current) = separate_old_and_current_hops(merged)
# plot_source_route(current, old)
# plt.title(rt_tbl_file)
# plot_num_valid_hops(merged)
# plt.title(rt_tbl_file)