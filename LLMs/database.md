请你创建一个5人团队，1个产品经理兼顾架构师（设计数据库），1个react前端，1个rust，1个c#

请你优先修改rust+react的tauri版本！因为我主要在测试这个版本其他的你先一并修改了，我并不会立马测试，后续有问题，我在修改！

# 账单分析功能调整

“对方名称”，需要查询数据库寻找对应的position与room,最后显示room,也就是多加一行，合并的数据库多一列用于存储翻译的，然后就是合并的数据库允许用户额外添加字符串备注！

## 账单分析模块

账单分析，要有各种统计图！

比如这个月洗澡花了多少钱。
你先写吧，最后我再来调整！

## 数据库

数据库存储于database/bill，存储为toml格式，我的github url为https://github.com/a645162/shmtu-terminal，如果本地不存在，则从github的main分支下载！

创建一些公共的toml吧！能够支持github云更新！作为一个数据库！
更新类型识别，比如存在什么关键词，就是识别为洗澡。
或者将某些名称翻译为具体的名称，比如你参考`/home/konghaomin/Prj/SHMTU/Digital-SHMTU-Tools/Database/Bill`目录下的：

```bash
cat position.json 
{
  "field": "target",
  "keywords": {
    "A食堂1楼大餐厅": {
      "position": "海馨楼",
      "room": "海馨第1食堂"
    },
    "A食堂1楼小餐厅": {
      "position": "海馨楼",
      "room": "海馨第3食堂"
    },
    "A食堂1楼清真餐厅": {
      "position": "海馨楼",
      "room": "海馨第5食堂(清真)"
    },
    "A食堂2楼大餐厅": {
      "position": "海馨楼",
      "room": "海馨第2食堂"
    },
    "A食堂2楼小餐厅": {
      "position": "海馨楼",
      "room": "海馨第4食堂"
    },
    "B食堂1楼": {
      "position": "海琴楼",
      "room": "海琴1楼"
    },
    "B食堂2楼": {
      "position": "海琴楼",
      "room": "海琴1楼"
    },
    "C1大餐厅": {
      "position": "海联楼",
      "room": "海联1楼"
    },
    "C食堂2楼": {
      "position": "海联楼",
      "room": "海联2楼"
    }
  }
}
cat type.json 
{
  "deposit": {
    "name": [
      "中行云充值",
      "微信充值"
    ]
  },
  "electricity": {
    "name": [
      "电费缴费"
    ]
  },
  "bath": {
    "target": [
      "淋浴",
      "热水"
    ]
  },
  "hot_water": {
    "name": [
      "水控转账"
    ]
  },
  "cake": {
    "target": [
      "北区西点房"
    ]
  },
  "canteen": {
    "target": [
      "食堂",
      "餐厅"
    ]
  }
}
cat schedule.json 
[
  {
    "valid_date": {
      "start_date": "2019.9.1",
      "end_date": "now"
    },
    "timetable": {
      "breakfast": {
        "name": "早餐",
        "start_time": "6:30",
        "end_time": "8:30"
      },
      "lunch": {
        "name": "午餐",
        "start_time": "10:45",
        "end_time": "12:30"
      },
      "dinner": {
        "name": "晚餐",
        "start_time": "16:30",
        "end_time": "18:15"
      },
      "midnight_snack": {
        "name": "夜宵",
        "start_time": "18:15",
        "end_time": "21:00"
      }
    }
  }
]
```
