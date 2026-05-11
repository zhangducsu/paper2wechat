/**
 * 微信公众号推文一键提取工具
 * 
 * 使用方法：
 * 1. 在浏览器中新建一个书签
 * 2. 将下面的代码粘贴到书签的"网址/URL"栏
 * 3. 打开任意微信公众号推文
 * 4. 点击该书签 → 正文HTML自动复制到剪贴板
 * 5. 回到Claude Code → Ctrl+V粘贴即可
 * 
 * 注意：在微信文章阅读页面使用，不要在公众号列表页使用
 */

// === 书签代码（复制下面这整行到书签URL栏） ===
javascript:void(function(){var c=document.getElementById('js_content');if(!c){alert('未找到正文区域，请在微信推文阅读页使用');return}var h=c.outerHTML;var b=new Blob([h],{type:'text/html'});var r=new FileReader;r.onload=function(){var t=r.result;navigator.clipboard.writeText(t).then(function(){alert('✅ 正文HTML已复制到剪贴板！\n\n回到Claude Code粘贴即可。')}).catch(function(){var ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);alert('✅ 正文HTML已复制到剪贴板！\n\n回到Claude Code粘贴即可。')})};r.readAsText(b)})();

// === 分行版本（方便阅读，实际使用时需压缩为一行） ===
javascript:void(function(){
  var c = document.getElementById('js_content');
  if (!c) {
    alert('未找到正文区域，请在微信推文阅读页使用');
    return;
  }
  var h = c.outerHTML;
  var b = new Blob([h], {type: 'text/html'});
  var r = new FileReader();
  r.onload = function() {
    var t = r.result;
    navigator.clipboard.writeText(t).then(function() {
      alert('✅ 正文HTML已复制到剪贴板！\n\n回到Claude Code粘贴即可。');
    }).catch(function() {
      var ta = document.createElement('textarea');
      ta.value = t;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      alert('✅ 正文HTML已复制到剪贴板！\n\n回到Claude Code粘贴即可。');
    });
  };
  r.readAsText(b);
})();
