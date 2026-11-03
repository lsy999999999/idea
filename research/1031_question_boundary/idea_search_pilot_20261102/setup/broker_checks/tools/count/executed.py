import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/setup/uci186.csv')
TABLES={"main":DF}
import json
print(json.dumps({"rows":len(DF)}))