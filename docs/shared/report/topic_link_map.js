/*  topic_link_map.js  –  Shared topic → practice-module link registry
 *  Browser IIFE – exposes window.AIMathTopicLinkMap
 *
 *  To add a new module: add ONE entry to TOPIC_LINK_MAP below.
 *  All engines (recommendation, practice-from-wrong, weakness-links)
 *  will pick it up automatically.
 */
(function(){
  'use strict';

  var TOPIC_LINK_MAP = {
    'commercial-pack1-fraction-sprint': '../commercial-pack1-fraction-sprint/',
    'fraction-word': '../fraction-word-g5/',
    'fraction-g5': '../fraction-g5/',
    'fraction': '../fraction-g5/',
    'mixed-multiply': '../mixed-multiply/',
    'decimal-unit4': '../decimal-unit4/',
    'decimal': '../interactive-decimal-g5/',
    'ratio': '../ratio-percent-g5/',
    'percent': '../ratio-percent-g5/',
    'volume': '../volume-g5/',
    'life': '../life-applications-g5/',
    'empire': '../interactive-g5-empire/',
    'core': '../interactive-g56-core-foundation/',
    'task': '../task-center/',
    'national-bank': '../interactive-g5-national-bank/',
    'midterm': '../interactive-g5-midterm1/',
    'grand-slam': '../g5-grand-slam/'
  };

  var DEFAULT_LINK = '../star-pack/';

  function getTopicLink(topic){
    var key = String(topic || '').toLowerCase();
    var entries = Object.keys(TOPIC_LINK_MAP);
    for (var index = 0; index < entries.length; index++) {
      if (key.indexOf(entries[index]) >= 0) return TOPIC_LINK_MAP[entries[index]];
    }
    return DEFAULT_LINK;
  }

  window.AIMathTopicLinkMap = {
    TOPIC_LINK_MAP: TOPIC_LINK_MAP,
    DEFAULT_LINK: DEFAULT_LINK,
    getTopicLink: getTopicLink
  };
})();
