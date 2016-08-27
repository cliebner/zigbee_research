__author__ = 'christina'

import matplotlib.pyplot as plt
import pandas as pd
import datetime as dt

# global variables:
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
PARSE_LOAD_LIST = [LOW_ADDR, SN, NAME, F_BIT]
PARSE_MAP_FILE = [NAME, SN, F_BIT, LOW_ADDR]
PARSE_RT_TBL = [LIST_NUM, LOW_ADDR, MY_ADDR, COUNT, H1, H2, H3, H4, H5, H6, H7, H8]
OLD_COUNT = 'old count'
MAX_PATH_LENGTH = 8
COLOR_WHEEL = ['black', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'magenta', 'gray']
COORDINATOR_DUMMY_VALUE = -1  # when COUNT == 0, replaces the initial '0000' to represent the coordinator
PHANTOM_DUMMY_VALUE = -2  # replaces network ids that no longer exist
FILLER_DUMMY_VALUE = -10  # replaces '0000' for graphing entire routing table


class RoutingTable(object):

    def __init__(self, route_table_filename, spc_list_filename, spc_type=1, file_date=dt.datetime.now()):
        self.route_table_filename = route_table_filename
        self.spc_list_filename = spc_list_filename
        self.spc_type = spc_type
        self.file_date = file_date
        self.route_table = self.get_routing_table_dataframe()
        self.spc_list = self.get_spc_file_dataframe(self.spc_type)
        self.spc_table = self.merge_route_table_to_spc_list()
        (self.old_hops, self.current_hops) = self.separate_old_and_current_hops()

    def get_routing_table_dataframe(self):
        f = open(self.route_table_filename, 'r')
        cleaned_response = self.parse_command_response(f, 'rt-tbl', PARSE_RT_TBL)
        routing_table = pd.DataFrame(cleaned_response, columns=PARSE_RT_TBL)
        old_hops = self.count_old_hops(routing_table)
        routing_table[OLD_COUNT] = old_hops
        return routing_table

    def get_spc_file_dataframe(self, file_type=1):
        # create a dataframe from the console output from command '3':
        if file_type == 0:
            f = open(self.spc_list_filename, 'r')
            cleaned_response = self.parse_command_response(f, 'load list', PARSE_LOAD_LIST)
            f.close()
            mapping_file_df = pd.DataFrame(cleaned_response, columns=PARSE_LOAD_LIST)
        # creates dataframe from a tab-delimited mapping file:
        else:
            mapping_file_df = pd.read_csv(self.spc_list_filename, sep='\t', names=PARSE_MAP_FILE)
            mapping_file_df[LOW_ADDR] = mapping_file_df[LOW_ADDR].apply(lambda x: x.lower())
        return mapping_file_df

    @staticmethod
    def parse_command_response(f, command, parse_list):
        cleaned_response = []
        low_addr = []
        line_start = 'Resp: ' + COMMANDS[command] + ','
        for line in f:
            if line_start in line and line.count(',') > 2 and 'fffe' not in line:
                cleaned_line = line.lstrip(line_start).strip().lower().split(',')
                # Depending on the type of file, we may need to clean up the data before storing into a dataframe:
                if LIST_NUM in parse_list:
                    # convert list id from string to int to allow for operations:
                    cleaned_line[parse_list.index(LIST_NUM)] = int(cleaned_line[parse_list.index(LIST_NUM)])
                if COUNT in parse_list:
                    # convert zigbee count from string to int to allow for operations:
                    cleaned_line[parse_list.index(COUNT)] = int(cleaned_line[parse_list.index(COUNT)])

                #  since we only care about the most updated response from an SPC within any text file, we should
                # replace the dataframe with the newest info as we read the file line by line.
                if cleaned_line[parse_list.index(LOW_ADDR)] in low_addr:
                    cleaned_response[low_addr.index(cleaned_line[parse_list.index(LOW_ADDR)])] = cleaned_line
                else:
                    low_addr.append(cleaned_line[parse_list.index(LOW_ADDR)])
                    cleaned_response.append(cleaned_line)
        return cleaned_response

    def merge_route_table_to_spc_list(self):
        return pd.DataFrame.merge(self.spc_list, self.route_table, on=LOW_ADDR).sort_values(by=NAME)

    def map_my_addr_to_index(self):
        my_address_map = dict(zip(self.spc_table.loc[:, MY_ADDR], self.spc_table.index))
        my_address_map['0000'] = FILLER_DUMMY_VALUE
        # '0000' can either mean the coordinator if COUNT == 0 or 'not used' if COUNT > 0
        return my_address_map

    def count_old_hops(self, rt_tbl_df):
        source_table_only = rt_tbl_df.loc[:, [H1, H2, H3, H4, H5, H6, H7, H8]]
        return source_table_only.apply(lambda x: MAX_PATH_LENGTH - list(x).count('0000'), axis=1)

    def separate_old_and_current_hops(self):
        address_map = self.map_my_addr_to_index()
        old_hops = self.spc_table.copy()
        current_hops = self.spc_table.copy()

        for i in range(1, MAX_PATH_LENGTH + 1):
            for j in self.spc_table.index:  # for each SPC, compare the zigbee hop count to the hop iteration you are on
                # if COUNT = 0, then anything in hop list is "old" and hop 1 is directly to coordinator
                # if COUNT < HOP_LIST iteration, then this hop is "old" (set current to DUMMY VALUE)
                # if COUNT > HOP_LIST iteration, then this hop is "current" (set old to DUMMY VALUE)
                # at any time, if MY_ADDR does not exist, set to PHANTOM VALUE
                # address_map[]
                # if self.spc_table.loc[j, HOP_LIST[i - 1]] != '0000': # this is handled with address_map!!!
                if self.spc_table.loc[j, COUNT] == 0:
                    if i == 1:
                        # node routes directly to coordinator
                        current_hops.loc[j, HOP_LIST[i - 1]] = COORDINATOR_DUMMY_VALUE
                    else:
                        current_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                    # everything else is old
                    try:
                        old_hops.loc[j, HOP_LIST[i - 1]] = address_map[self.spc_table.loc[j, HOP_LIST[i - 1]]]
                    except KeyError:
                        old_hops.loc[j, HOP_LIST[i - 1]] = PHANTOM_DUMMY_VALUE

                elif self.spc_table.loc[j, COUNT] >= i:
                    # send SPC to current hops bucket + put dummy filler value in old hops bucket
                    try:
                        current_hops.loc[j, HOP_LIST[i - 1]] = address_map[self.spc_table.loc[j, HOP_LIST[i-1]]]
                    except KeyError:
                        current_hops.loc[j, HOP_LIST[i - 1]] = PHANTOM_DUMMY_VALUE
                    old_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                else:
                    # send SPC to old hops bucket + put dummy filler value in current hops bucket
                    try:
                        old_hops.loc[j, HOP_LIST[i - 1]] = address_map[self.spc_table.loc[j, HOP_LIST[i - 1]]]
                    except KeyError:
                        old_hops.loc[j, HOP_LIST[i - 1]] = PHANTOM_DUMMY_VALUE
                    current_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                # else:
                #     current_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
                #     old_hops.loc[j, HOP_LIST[i - 1]] = FILLER_DUMMY_VALUE
        return old_hops, current_hops

    def plot_source_route(self):
        # TODO: may want to paint the "coordinator" values a different color from "hop 1" values...
        plt.figure(figsize=(22, 22))
        plt.plot(self.current_hops.index, self.current_hops.index, 'k-')
        [plt.plot(self.current_hops.index, self.current_hops[HOP_LIST[i]],
                  color=COLOR_WHEEL[i], marker='o', mec='None', markersize=10, linestyle='None')
         for i in range(0, MAX_PATH_LENGTH)]
        [plt.plot(self.old_hops.index, self.old_hops[HOP_LIST[i]],
                  color='None', marker='o', mec=COLOR_WHEEL[i], markersize=10, linestyle='None')
         for i in range(0, MAX_PATH_LENGTH)]
        plt.xticks(self.current_hops.index, self.current_hops.loc[:, NAME], rotation=90, fontsize=8)
        plt.yticks([PHANTOM_DUMMY_VALUE, COORDINATOR_DUMMY_VALUE] + list(self.current_hops.index),
                   ['phantom', 'coordinator'] + list(self.current_hops.loc[:, NAME]),
                   fontsize=8)
        plt.grid(True, which='major', axis='both')
        plt.xlim(0, len(self.current_hops.index))
        plt.ylim(PHANTOM_DUMMY_VALUE - 1, len(self.current_hops.index))
        plt.xlabel('SPC (' + self.spc_list_filename + ')')
        plt.ylabel('SPCs in Route')
        plt.legend(['self', H1, H2, H3, H4, H5, H6, H7, H8, 'invalid'], loc='center left', bbox_to_anchor=(1.0, 0.5))
        plt.title('Source Routing Paths: ' + self.route_table_filename)

    def plot_hops_frequency(self):
        plt.figure(figsize=(5, 5))
        zeros = pd.Series((MAX_PATH_LENGTH + 1) * [0])
        frequency = self.route_table[COUNT].value_counts(sort=False)/len(self.route_table[COUNT])
        plt.plot(frequency.add(zeros, fill_value=0), 'bo-')
        plt.ylim(0, 1.0)
        plt.xlabel('Number of Hops')
        plt.ylabel('Frequency')
        plt.title(self.route_table_filename)

    def plot_num_valid_hops(self):
        plt.figure(figsize=(22, 8))
        plt.plot(self.spc_table[COUNT], 'bo')
        plt.xticks(self.spc_table.index, self.spc_table.loc[:, NAME], rotation=90, fontsize=8)
        plt.ylim(0, 5)
        plt.xlabel('SPC')
        plt.ylabel('Number of valid hops on route')
        plt.title(self.route_table_filename)


class RoutingTableHistory(object):
    def __init__(self, routing_table_list):
        self.routing_table_list = list(routing_table_list)

    def print_dates(self):
        for rt in self.routing_table_list:
            print dt.datetime.strftime(rt.file_date, '%Y-%m-%d %H:%M')

    def plot_frequencies(self):
        [x.plot_hops_frequency() for x in self.routing_table_list]

    def get_changes(self):
        # this method quantifies the change in routing tables from one file to the next
        # metric = 0: if a node's current routing table, rt_i, shares none of the routes from the previous, rt_i-1
        # metric = 1: if all routes in rt_i are in rt_i-1
        # metric < 1: if all routes in rt_i are in rt_i-1 and len(rt_i) < len(rt_i-1)
        # metric > 1: if all routes in rt_i-1 are in rt_i and len(rt_i) > len (rt_i-1)
        # TODO: think about a metric to capture how many invalid routes remain in table?
        pass
