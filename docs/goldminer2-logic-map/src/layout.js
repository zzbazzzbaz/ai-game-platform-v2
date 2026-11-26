export const LAYOUT = {
  "loop": {
    "positions": {
      "start": [
        30,
        280
      ],
      "swing": [
        225,
        280
      ],
      "launch": [
        420,
        280
      ],
      "hit": [
        615,
        280
      ],
      "grab": [
        810,
        105
      ],
      "score": [
        1005,
        105
      ],
      "check": [
        1005,
        280
      ],
      "pass": [
        1200,
        280
      ],
      "miss": [
        810,
        455
      ]
    },
    "routes": {
      "check->swing": {
        "side": "bottom",
        "at": 660
      },
      "miss->swing": {
        "side": "bottom",
        "at": 520
      }
    },
    "bounds": [
      1390,
      675
    ],
    "types": {
      "start": "start",
      "swing": "action",
      "launch": "action",
      "hit": "decision",
      "grab": "action",
      "score": "reward",
      "check": "decision",
      "pass": "end",
      "miss": "note"
    }
  },
  "states": {
    "positions": {
      "login": [
        80,
        30
      ],
      "menu": [
        340,
        30
      ],
      "map": [
        340,
        175
      ],
      "play": [
        340,
        320
      ],
      "pause": [
        600,
        320
      ],
      "result": [
        340,
        465
      ]
    },
    "routes": {
      "menu->login": {
        "side": "bottom",
        "at": 142
      },
      "result->play": {
        "side": "right",
        "at": 820
      },
      "result->map": {
        "side": "right",
        "at": 880
      }
    },
    "bounds": [
      910,
      620
    ],
    "types": {
      "login": "action",
      "menu": "start",
      "map": "action",
      "play": "action",
      "pause": "note",
      "result": "reward"
    }
  },
  "hook": {
    "positions": {
      "h-launch": [
        30,
        260
      ],
      "h-scan": [
        220,
        260
      ],
      "h-hit": [
        410,
        260
      ],
      "h-grab": [
        600,
        110
      ],
      "h-collect": [
        800,
        110
      ],
      "h-swing": [
        1010,
        260
      ],
      "h-extend": [
        600,
        430
      ],
      "h-max": [
        800,
        430
      ],
      "h-empty": [
        1010,
        430
      ]
    },
    "routes": {
      "h-max->h-hit": {
        "side": "bottom",
        "at": 555
      }
    },
    "bounds": [
      1270,
      600
    ],
    "types": {
      "h-launch": "action",
      "h-scan": "action",
      "h-hit": "decision",
      "h-grab": "action",
      "h-collect": "reward",
      "h-swing": "note",
      "h-extend": "action",
      "h-max": "decision",
      "h-empty": "note"
    }
  },
  "levels": {
    "positions": {
      "lv1": [
        40,
        120
      ],
      "lv2": [
        240,
        120
      ],
      "lv3": [
        440,
        120
      ],
      "lv4": [
        640,
        120
      ],
      "lv5": [
        840,
        120
      ],
      "v-stone": [
        40,
        330
      ],
      "v-gold": [
        240,
        330
      ],
      "v-diamond": [
        440,
        330
      ],
      "v-stars": [
        640,
        330
      ],
      "v-save": [
        840,
        330
      ]
    },
    "bounds": [
      1040,
      500
    ],
    "types": {
      "lv1": "level",
      "lv2": "level",
      "lv3": "level",
      "lv4": "level",
      "lv5": "level",
      "v-stone": "stone",
      "v-gold": "gold",
      "v-diamond": "diamond",
      "v-stars": "star",
      "v-save": "save"
    }
  }
};
