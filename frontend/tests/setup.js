/**
 * Jest global setup – mocks browser globals so JS files can be required() directly.
 */
const { IDBFactory, IDBKeyRange } = require("fake-indexeddb");

// IndexedDB
global.indexedDB  = new IDBFactory();
global.IDBKeyRange = IDBKeyRange;

// localStorage stub
let _lsStore = {};
global.localStorage = {
  get _store() { return _lsStore; },
  set _store(v) { _lsStore = v; },
  getItem:    (k) => _lsStore[k] ?? null,
  setItem:    (k, v) => { _lsStore[k] = v; },
  removeItem: (k) => { delete _lsStore[k]; },
  clear:      () => { _lsStore = {}; },
};

// Chart.js mock (used by wp_chart.js, stats_dashboard.js render functions)
function makeMockChartInstance() {
  return {
    data: { labels: [], datasets: [{ data: [50, 55], pointRadius: [4, 4] }] },
    update: jest.fn(),
    destroy: jest.fn(),
  };
}
global.Chart = jest.fn().mockImplementation(() => makeMockChartInstance());

// DOM mock (used by render functions)
function makeMockElement() {
  return {
    getContext: () => ({}),
    style: {},
    _html: "",
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = v; },
    querySelectorAll: jest.fn(() => []),
    addEventListener: jest.fn(),
  };
}
global.document = {
  getElementById: jest.fn(() => makeMockElement()),
  createElement: jest.fn(() => makeMockElement()),
};

// window stub (used by modules for self-registration)
global.window = {
  ChessDB: null,
  Chart:   undefined,
  Chess:   undefined,
  app:     null,
};

// Reset IDB + localStorage + mocks before each test
beforeEach(() => {
  global.indexedDB  = new IDBFactory();
  _lsStore = {};
  global.window.ChessDB = null;
  if (global.Chart && global.Chart.mockClear) global.Chart.mockClear();
  if (global.document && global.document.getElementById && global.document.getElementById.mockClear) {
    global.document.getElementById.mockClear();
  }
});
