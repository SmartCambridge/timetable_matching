Pandas notes
============

```
import pandas as pd
data = pd.read_csv('Work/icp/timetable-matching/rows-2018-09-21.csv')

data.describe()
data[1]
data['Type'].value_counts()
data['Delay_Departure'].describe()
data['Delay_Arrival'].describe()
```