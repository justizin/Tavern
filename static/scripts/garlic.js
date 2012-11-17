/* version 0.0.4 http://garlicjs.org */
!function(a){"use strict";var b=function(){this.defined="undefined"!=typeof localStorage?!0:!1};b.prototype={constructor:b,get:function(a,b){return localStorage.getItem(a)?localStorage.getItem(a):b!==void 0?b:null},has:function(a){return localStorage.getItem(a)?!0:!1},set:function(a,b){return localStorage.setItem(a,b),!0},destroy:function(a){return localStorage.removeItem(a),!0},clean:function(){for(var a=localStorage.length-1;a>=0;a--)-1!==localStorage.key(a).indexOf("garlic:")&&localStorage.removeItem(localStorage.key(a));return!0},clear:function(){localStorage.clear()}};var c=function(a,b,c){this.init("garlic",a,b,c)};c.prototype={constructor:c,init:function(b,c,d,e){this.type=b,this.$element=a(c),this.options=this.getOptions(e),this.storage=d,this.path=this.$element.getPath(),this.$element.context.form&&(this.retrieve(),this.$element.on(this.options.events.join("."+this.type+" "),!1,a.proxy(this.persist,this)),this.$element.closest("form").on("submit",!1,a.proxy(this.destroy,this)),this.$element.addClass("garlic-auto-save"))},getOptions:function(b){return b=a.extend({},a.fn[this.type].defaults,b,this.$element.data())},persist:function(){this.options.storage&&this.storage.set(this.path,this.$element.context.value)},retrieve:function(){this.storage.has(this.path)&&this.$element.val(this.storage.get(this.path))},destroy:function(){this.storage.destroy(this.path)},remove:function(){this.remove(),this.$element.val("")}},a.fn.getPath=function(){if(this.length!=1)return!1;var a,b=this;while(b.length){var c=b[0],d=c.localName;if(!d)break;d=d.toLowerCase();var e=b.parent(),f=e.children(d);f.length>1&&(d+=":eq("+f.index(c)+")"),a=d+(a?">"+a:""),b=e}return"garlic:"+document.domain+">"+a},a.fn.garlic=function(e){function h(b){var d=a(b),h=d.data("garlic");h||d.data("garlic",h=new c(b,g,f)),typeof e=="string"&&h[e]!==void 0&&h[e]()}var f=a.extend({},a.fn.garlic.defaults,e,this.data()),g=new b;return g.defined?(f.debug&&(window.garlicStorage=g),this.each(function(){a(this).is("form")&&a(this).find(f.inputs).each(function(){h(a(this))}),a(this).is(d.supportedInputs)&&h(a(this))})):!1},a.fn.garlic.Constructor=c;var d={supportedInputs:"input:text, textarea, select"};a.fn.garlic.defaults={debug:!1,storage:!0,inputs:"input:text, textarea",events:["DOMAttrModified","textInput","input","change","keypress","paste","focus"]},a(window).on("load",function(){a('[data-persist="garlic"]').each(function(){a(this).garlic()})})}(window.jQuery)