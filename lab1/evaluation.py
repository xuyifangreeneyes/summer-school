import evaluation_utils as eval_utils
import json
import statistics as stats
import range_query as rq
import learn_from_data
import learn_from_query


def gen_report(act, est_results):
    f = open("./eval/report.md", "w")
    f.write("| name | p50 | p80 | p90 | p99 |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for name in est_results:
        est = est_results[name]
        eval_utils.draw_act_est_figure(name, act, est)
        p50, p80, p90, p99 = eval_utils.cal_p_error_distribution(act, est)
        f.write("| %s | %.2f | %.2f | %.2f | %.2f |\n" % (name, p50, p80, p90, p99))

    f.write("\n")
    for name in est_results:
        f.write("![%s](%s.png)\n\n" % (name, name))
    f.close()


def est_spn(csvfile, train_data, table_stats):
    print("SPN estimation on %s" % csvfile)
    col_names = ['kind_id', 'production_year', 'imdb_id', 'episode_of_id', 'season_nr', 'episode_nr']
    col_offsets = [3, 4, 5, 7, 8, 9]
    spn = learn_from_data.SPN.construct_from_csvfile(csvfile, col_names, col_offsets)

    est = []
    for item in train_data:
        range_query = rq.ParsedRangeQuery.parse_range_query(item['query'])
        sel = spn.estimate(range_query)
        est.append(sel * table_stats.row_count)
    return est


if __name__ == '__main__':
    stats_json_file = 'data/title_stats.json'
    train_json_file = 'data/query_train_2000.json'
    test_json_file = 'data/query_test_2000.json'
    columns = ['kind_id', 'production_year', 'imdb_id', 'episode_of_id', 'season_nr', 'episode_nr']

    table_stats = stats.TableStats.load_from_json_file(stats_json_file, columns)
    with open(train_json_file, 'r') as f:
        train_data = json.load(f)
    with open(test_json_file, 'r') as f:
        test_data = json.load(f)

    est_avi, est_ebo, est_min_sel, act = [], [], [], []
    for item in train_data:
        range_query = rq.ParsedRangeQuery.parse_range_query(item['query'])
        est_avi.append(stats.AVIEstimator.estimate(range_query, table_stats) * table_stats.row_count)
        est_ebo.append(stats.ExpBackoffEstimator.estimate(range_query, table_stats) * table_stats.row_count)
        est_min_sel.append(stats.MinSelEstimator.estimate(range_query, table_stats) * table_stats.row_count)
        act.append(item['act_rows'])

    est_spn_sample_1000 = est_spn('./data/title_sample_1000.csv', train_data, table_stats)
    est_spn_sample_10000 = est_spn('./data/title_sample_10000.csv', train_data, table_stats)
    est_spn_sample_20000 = est_spn('./data/title_sample_20000.csv', train_data, table_stats)

    est_mlp, _, _, _ = learn_from_query.est_mlp(train_data, test_data, table_stats, columns)
    est_xgb, _, _, _ = learn_from_query.est_xgb(train_data, test_data, table_stats, columns)

    gen_report(act, {
        "avi": est_avi,
        "ebo": est_ebo,
        "min_sel": est_min_sel,
        "spn_sample_1000": est_spn_sample_1000,
        "spn_sample_10000": est_spn_sample_10000,
        "spn_sample_20000": est_spn_sample_20000,
        "mlp": est_mlp,
        "xgb": est_xgb,
    })
