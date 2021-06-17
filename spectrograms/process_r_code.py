from rpy2 import robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

from rpy2.robjects.conversion import localconverter


def run_analysis(data):
    base = importr('base')

    base.source("VolcSeismo.R")
    r_func = robjects.globalenv['runAnalysis']
    with localconverter(robjects.default_converter + pandas2ri.converter):
        result = r_func(data)
        # pd_result = robjects.conversion.rpy2py(result)

    print(result)


if __name__ == "__main__":
    import pandas

    # test file
    df = pandas.read_csv("WACK_2021_06_03_14_50_09.csv")
    run_analysis(df)
