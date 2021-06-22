import os

from rpy2 import robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

from rpy2.robjects.conversion import localconverter


def run(data, station):
    base = importr('base')

    # Load the R script
    script_path = os.path.join(os.path.dirname(__file__), 'VolcSeismo.R')
    base.source(script_path)
    r_func = robjects.globalenv['runAnalysis']
    with localconverter(robjects.default_converter + pandas2ri.converter):
        result = r_func(data)

    # TODO: Save result to DB
    print("Saving result for", station)
    return result


if __name__ == "__main__":
    import pandas

    # test file
    df = pandas.read_csv("WACK_2021_06_03_14_50_09.csv")
    result = run(df)
    result.to_csv('pythonResult.csv')

