__author__ = 'christina'

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import routing_tables as rt

# user can configure a block layout for plotting or allow default (linear)
# user uploads a csv
# user can upload many csvs for a single block
# for each broadcast: min, mean, mode, median, max response time
# for each SPC: num broadcasts received, min/mean/max time between received and read back
# for any run: identify best/worst responsive SPC
# for any run: playback messages
# for any run: order SPCs by response time

# define a class for the block
# block has a layout
# block has a list of csv results
# new class for a csv result
# csv has stats
# csv had plots
# an SPC has stats

BOOLEAN_SWITCH = {
    'y': True,
    'yes': True,
    'n': False,
    'no': False,
}

TIME_BC = 'broadcast time'
VALUE_BC = 'broadcast value'
TIME_REQUEST = 'request time'
TIME_RESPONSE = 'response time'
VALUE_RESPONSE = 'response value'
IS_RESPONSIVE = 'responded?'
IS_DROPPED = 'missed BC value?'
VALUE_DROPPED = 'missed value'
VALUE_REPEAT = 'repeated value'
TIME_RESPONSE_REQUEST = 'response - request timedelta'
TIME_REQUEST_BC = 'request - broadcast timedelta'
VALUE_DUMMY = -1

CONVERT_COLUMN = {
    TIME_BC: (lambda x: pd.to_datetime(x)),
    TIME_REQUEST: (lambda x: pd.to_datetime(x)),
    TIME_RESPONSE: (lambda x: pd.to_datetime(x)),
    VALUE_BC: (lambda x: pd.to_numeric(x)),
    VALUE_RESPONSE: (lambda x: pd.to_numeric(x)),
}

TIMES = [TIME_BC, TIME_REQUEST, TIME_RESPONSE]
VALUES = [VALUE_BC, VALUE_RESPONSE]

class NewNCUBlock(object):

    def __init__(self, name):
        self.name = name
        self.layout = get_layout()
        self.results_list = []
        self.SPC_list = []

    def __str__(self):
        return self.name + ': ' + str(len(self.SPC_list)) + ' SPCs'

    def load_spc_list(self, filename):
        f = open(filename, 'r')
        self.SPC_list = f


class BroadcastResult(object):
    COORDS = np.array([1, 1])  # placeholder for inheriting layout from NCUBlock class

    def __init__(self, filename):
        f = open(filename, 'r')
        self.filename = filename
        # chunk out broadcast
        # chunk out SPC broadcast response
        # chunk out source tables each broadcast
        self.broadcast_df, self.broadcasts_dict, self.routing_tables_dict, self.lowaddr_spc_map = parse_results_file(f)
        self.name_coord_map, self.coord_name_map = self.get_spc_layout()
        self.broadcasts_timedelta = self.get_broadcast_metrics()
        self.response_time_spc, self.response_time_broadcast = self.plot_response_time()


        # self.spc_rt_change = self.get_rt_change_per_spc(self)
        f.close()

    def get_spc_layout(self):
        # TODO: inherit user-defined custom layout from superclass
        # create num array for length of spcs
        linear_coords = range(1, len(self.lowaddr_spc_map) + 1)
        names = self.broadcasts_dict.keys()  # format is 'name,lowaddr'
        names.sort()
        layout = dict(zip(names, linear_coords))
        layout_inv = dict(zip(linear_coords, names))
        return layout, layout_inv

    def plot_response_time(self):
        plt.suptitle(self.filename)
        response_time_by_spc = pd.DataFrame({
                                        self.name_coord_map[b[0]]: b[1][TIME_RESPONSE_REQUEST]
                                        for b in self.broadcasts_timedelta.iteritems()},
                                    index=self.broadcast_df[VALUE_BC])
        ax_1 = plt.subplot(2, 1, 1)
        ax_1.plot(response_time_by_spc, marker='.')
        ax_1.legend([self.coord_name_map[spc] for spc in response_time_by_spc.columns])
        ax_1.set_xlim([0, len(response_time_by_spc.index) + 1])
        ax_1.set_xlabel(VALUE_BC)
        ax_1.set_ylabel(TIME_RESPONSE_REQUEST)


        # plot response time against SPC
        response_time_by_broadcast_value = response_time_by_spc.transpose()
        ax_2 = plt.subplot(2, 1, 2)
        ax_2.plot(response_time_by_broadcast_value, marker='.')
        ax_2.legend(response_time_by_broadcast_value.columns)
        ax_2.set_xlim([0, len(response_time_by_broadcast_value.index) + 1])
        ax_2.set_xticks(response_time_by_broadcast_value.index)
        ax_2.set_xticklabels([self.coord_name_map[b] for b in response_time_by_broadcast_value.index])
        plt.ylabel(TIME_RESPONSE_REQUEST)
        return response_time_by_spc.rename(columns=self.coord_name_map, inplace=True), response_time_by_broadcast_value

    def get_broadcast_metrics(self):
        for b in self.broadcasts_dict.iteritems():
            print b[0]
            b[1][IS_RESPONSIVE] = b[1][VALUE_RESPONSE] > 0
            b[1][IS_DROPPED] = b[1][VALUE_RESPONSE] != b[1][VALUE_BC]
            b[1][VALUE_DROPPED] = b[1][VALUE_BC][b[1][IS_DROPPED]]
            b[1][VALUE_REPEAT] = b[1][VALUE_RESPONSE][b[1][IS_DROPPED] & b[1][IS_RESPONSIVE]]
            # catch case if spc is completely unresponsive:
            try:
                b[1][TIME_RESPONSE_REQUEST] = pd.to_numeric(
                    b[1][b[1][IS_RESPONSIVE]][TIME_RESPONSE] - b[1][b[1][IS_RESPONSIVE]][TIME_REQUEST]) / 10 ** 9
            except TypeError:
                b[1][TIME_RESPONSE_REQUEST] = [VALUE_DUMMY] * len(b[1].index)

            try:
                b[1][TIME_REQUEST_BC] = pd.to_numeric(
                    b[1][b[1][IS_RESPONSIVE]][TIME_REQUEST] - b[1][b[1][IS_RESPONSIVE]][TIME_BC]) / 10 ** 9
            except TypeError:
                b[1][TIME_REQUEST_BC] = [VALUE_DUMMY] * len(b[1].index)
        return self.broadcasts_dict

    # def get_lowaddr_spc_map(self):
    #     # get list of spc names and low address from broadcasts dict
    #     lowaddr_spc_map = {b.split(',')[1].lower(): b.split(',')[0] for b in self.broadcasts_dict.keys()}
    #     spc_set = set(lowaddr_spc_map.keys())
    #
    #     # check list from broadcasts against low addresses found in routing tables:
    #     i = 0
    #     for r in self.routing_tables_dict.iteritems():
    #         set_diff = spc_set.symmetric_difference(set(r[1][rt.LOW_ADDR]))  # for debugging only
    #         for s in set_diff:
    #             if s not in spc_set:
    #                 lowaddr_spc_map[s] = 'unk_' + str(i)
    #                 i += 1
    #         spc_set.update(set(r[1][rt.LOW_ADDR]))
    #     return lowaddr_spc_map

    def get_rt_change_per_spc(self):
        # this method re-arranges the routing table dict so that each item is the timeline for an spc
        spc_rt_dict = {}
        for r in self.routing_tables_dict.iteritems():
            for adr in r[1][rt.LOW_ADDR]:
                spc_rt_dict[adr] = r[1][r[1][rt.LOW_ADDR] == adr]
        return spc_rt_dict


# def get_single_factor(a_dict, single_factor):
#     single_factor_df = pd.DataFrame({d[0]: d[1] for d in a_dict.iteritems()})

def parse_results_file(f):
    # "chunks" of results are delimited by a header line and a footer that is a newline

    broadcasts_dict = {}
    routing_tables_dict = {}
    chunk = []
    header = 'none'
    # TODO: could this be implemented recursively?
    is_chunk = False  # turn on when you find a header, turn off when you find a footer
    is_routingtables = False  # turn on when you find 'routes', which signifies start of the routing table chunk
    for line in f:
        if line != '\n' and is_chunk is False:  # header
            is_chunk = True
            header = line.strip()

            if 'routes' in header:  # special case for catching the routing tables:
                is_routingtables = True

        elif line != '\n' and is_chunk is True:  # chunk
            chunk.append(line.strip().split(','))

        elif line == '\n' and is_chunk is True or f.readline() is '':  # footer: saves results into dict and resets

            if is_routingtables is False:
                broadcasts_dict[header] = pd.DataFrame(chunk)
                if 'broadcasts' in header:
                    broadcasts_dict[header].columns = [TIME_BC, VALUE_BC]
                elif ',' in header:
                    broadcasts_dict[header].columns = [TIME_REQUEST, VALUE_BC, TIME_RESPONSE, VALUE_RESPONSE]
                else:
                    continue

                # convert column types
                time_cols = list(set(broadcasts_dict[header].columns).intersection(TIMES))
                value_cols = list(set(broadcasts_dict[header].columns).intersection(VALUES))
                broadcasts_dict[header][time_cols] = broadcasts_dict[header][time_cols].apply(
                    lambda x: pd.to_datetime(x, errors='ignore'))
                broadcasts_dict[header][value_cols] = broadcasts_dict[header][value_cols].apply(
                    lambda x: pd.to_numeric(x, errors='ignore'))

            # is_routingtables is True:

            # reset:
            is_chunk = False
            is_routingtables = False
            chunk = []
        else:
            continue

    # at end of file, now break up routing table chunk by timestamp:
    if is_routingtables is True:
        column_names = [rt.LIST_NUM, rt.LOW_ADDR, rt.MY_ADDR, rt.COUNT, rt.H1, rt.H2, rt.H3, rt.H4, rt. H5]  # TODO why only 5 hops instead of 8?
        # loop through chunk and break it up into timestamp-ed routing table chunks
        rt_chunk = []
        for c in chunk:
            if c[0].count(':') > 1 and len(rt_chunk) == 0:  # rt_chunk header
                header = c[0]
            elif c[0].count(':') > 1 and len(rt_chunk) > 0:  # rt chunk footer
                routing_tables_dict[header] = pd.DataFrame(rt_chunk, columns=column_names)
                routing_tables_dict[header]['timestamp'] = pd.to_datetime(pd.Series([header] * len(rt_chunk)))
                rt_chunk = []
                header = c[0]
            else:
                rt_chunk.append(c)
    broadcast_df = broadcasts_dict.pop('broadcasts')

    # broadcasts_dict = {b[0]: pd.DataFrame.merge(broadcast_df, b[1], on=VALUE_BC, how='left')
    #                    for b in broadcasts_dict.iteritems()}
    lowaddr_spc_map = {}
    for b in broadcasts_dict.iteritems():
        broadcasts_dict[b[0]] = pd.DataFrame.merge(broadcast_df, b[1], on=VALUE_BC, how='left')
        lowaddr_spc_map[b[0].split(',')[1].lower()] = b[0].split(',')[0]

    # get list of spc names and low address from broadcasts dict #########################################
    # lowaddr_spc_map = {b.split(',')[1].lower(): b.split(',')[0] for b in broadcasts_dict.keys()}
    spc_set = set(lowaddr_spc_map.keys())

    # check list from broadcasts against low addresses found in routing tables:
    i = 0
    for r in routing_tables_dict.iteritems():
        set_diff = spc_set.symmetric_difference(set(r[1][rt.LOW_ADDR]))  # for debugging only
        for s in set_diff:
            if s not in spc_set:
                lowaddr_spc_map[s] = 'unk_' + str(i)
                i += 1
        spc_set.update(set(r[1][rt.LOW_ADDR]))

    return broadcast_df, broadcasts_dict, routing_tables_dict, lowaddr_spc_map


def get_layout():
    is_custom = BOOLEAN_SWITCH.get(raw_input('Type y to enter block layout, or n to use default layout: ').lower(), None)
    if is_custom is True:
        x_y_coords = np.array([1, 1])
        names_list = []
        num_sections = 0
        is_add_section = True
        while is_add_section is True:
            num_sections += 1
            num_SPCs = float(raw_input('Number of SPCs in this section: '))
            start_name = float(raw_input('Numeric name of first SPC in this section (e.g. 101): '))
            names_list += range(start_name, start_name + num_SPCs + 1)
            is_add_section = BOOLEAN_SWITCH.get(raw_input('Add another section? y/n '), False)


    else:
        x_y_coords = np.array([0, 0])
    return x_y_coords


# test = BroadcastResult('spcData.txt')