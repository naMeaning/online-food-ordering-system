/** @type {import('tailwindcss').Config} */

module.exports = {
  content: [
    "./templates/**/*.html",        // 项目级模板
    "./**/templates/**/*.html",     // 各 app 的模板（如 menu/templates/）
    "./static/js/**/*.js"           // 你写的前端 JS 里也可能出现类名
  ],
  theme: {
    container: { center: true, padding: "1rem" },
    extend: {}
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography")
  ],
}

