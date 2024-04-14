"use strict";
exports.id = 794;
exports.ids = [794];
exports.modules = {

/***/ 43794:
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {


// EXPORTS
__webpack_require__.d(__webpack_exports__, {
  "Lp": () => (/* binding */ client),
  "C5": () => (/* binding */ getInfo),
  "KY": () => (/* binding */ setSession)
});

// EXTERNAL MODULE: ./node_modules/dify-client/index.js
var dify_client = __webpack_require__(92353);
// EXTERNAL MODULE: ./node_modules/uuid/dist/esm-node/v4.js + 3 modules
var v4 = __webpack_require__(94832);
;// CONCATENATED MODULE: ./config/index.ts
const APP_ID = `${"516ef55a-7741-4892-a008-b16b536aab71"}`;
const API_KEY = `${"app-uYnAtUj2Nhkh5wph8p6Ih43A"}`;
const API_URL = `${"https://api.idomy.cn/v1"}`;
const APP_INFO = {
    title: "Chat APP",
    description: "",
    copyright: "",
    privacy_policy: "",
    default_language: "zh-Hans"
};
const isShowPrompt = false;
const promptTemplate = "I want you to act as a javascript console.";
const API_PREFIX = "/api";
const LOCALE_COOKIE_NAME = "locale";
const DEFAULT_VALUE_MAX_LEN = 48;

;// CONCATENATED MODULE: ./app/api/utils/common.ts



const userPrefix = `user_${APP_ID}:`;
const getInfo = (request)=>{
    const sessionId = request.cookies.get("session_id")?.value || (0,v4/* default */.Z)();
    const user = userPrefix + sessionId;
    return {
        sessionId,
        user
    };
};
const setSession = (sessionId)=>{
    return {
        "Set-Cookie": `session_id=${sessionId}`
    };
};
const client = new dify_client/* ChatClient */.AM(API_KEY, API_URL || undefined);


/***/ })

};
;