define("mvc/visualization/chart/chart-client",["exports","utils/deferred","mvc/ui/ui-modal","mvc/ui/ui-misc","mvc/visualization/chart/components/model","mvc/visualization/chart/views/editor","mvc/visualization/chart/views/viewer","mvc/visualization/chart/views/menu","backbone"],function(t,e,i,a,s,r,n,d,h){"use strict";function l(t){return t&&t.__esModule?t:{default:t}}Object.defineProperty(t,"__esModule",{value:!0});var o=l(e),c=l(i),u=l(a),p=l(s),v=l(r),f=l(n),m=l(d),w=function(t){if(t&&t.__esModule)return t;var e={};if(null!=t)for(var i in t)Object.prototype.hasOwnProperty.call(t,i)&&(e[i]=t[i]);return e.default=t,e}(h);t.default=w.View.extend({initialize:function(t){var e=this;this.modal=window.parent.Galaxy&&window.parent.Galaxy.modal||new c.default.View,this.setElement($("<div/>").addClass("charts-client").append($("<div/>").addClass("charts-buttons")).append($("<div/>").addClass("charts-center")).append($("<div/>").addClass("charts-right"))),this.$center=this.$(".charts-center"),this.$right=this.$(".charts-right"),this.$buttons=this.$(".charts-buttons"),this.chart=new p.default({},t),this.chart.plugin=t.visualization_plugin,this.chart.plugin.specs=this.chart.plugin.specs||{},this.chart_load=t.chart_load,this.message=new u.default.Message,this.deferred=new o.default,this.viewer=new f.default(this),this.editor=new v.default(this),this.menu=new m.default(this),this.$center.append(this.viewer.$el),this.$right.append(this.message.$el).append(this.editor.$el),this.$buttons.append(this.menu.$el),$.ajax({url:Galaxy.root+"api/datasets/"+t.dataset_id}).done(function(t){e.dataset=t,e.chart.load(),e.chart.trigger("redraw")}).fail(function(t){var i=t.responseJSON&&t.responseJSON.err_msg;e.errormessage=i||"Import failed for unkown reason."})}})});