
head.ready(function() {
    head.js("/static/scripts/tooltip.js");

    
 $.fn.splitter = function(args){
    args = args || {};
    return this.each(function() {
        var zombie;     // left-behind splitbar for outline resizes
        function startSplitMouse(evt) {
            if ( opts.outline )
                zombie = zombie || bar.clone(false).insertAfter(A);
            panes.css("-webkit-user-select", "none");   // Safari selects A/B text on a move
            bar.addClass(opts.activeClass);
            A._posSplit = A[0][opts.pxSplit] - evt[opts.eventPos];
            $(document)
                .bind("mousemove", doSplitMouse)
                .bind("mouseup", endSplitMouse);
        }
        function doSplitMouse(evt) {
            var newPos = A._posSplit+evt[opts.eventPos];
            if ( opts.outline ) {
                newPos = Math.max(0, Math.min(newPos, splitter._DA - bar._DA));
                bar.css(opts.origin, newPos);
            } else 
                resplit(newPos);
        }
        function endSplitMouse(evt) {
            bar.removeClass(opts.activeClass);
            var newPos = A._posSplit+evt[opts.eventPos];
            if ( opts.outline ) {
                zombie.remove(); zombie = null;
                resplit(newPos);
            }
            panes.css("-webkit-user-select", "text");   // let Safari select text again
            $(document)
                .unbind("mousemove", doSplitMouse)
                .unbind("mouseup", endSplitMouse);
        }
        function resplit(newPos) {
            // Constrain new splitbar position to fit pane size limits
            newPos = Math.max(A._min, splitter._DA - B._max, 
                    Math.min(newPos, A._max, splitter._DA - bar._DA - B._min));
            // Resize/position the two panes
            bar._DA = bar[0][opts.pxSplit];     // bar size may change during dock
            bar.css(opts.origin, newPos).css(opts.fixed, splitter._DF);
            A.css(opts.origin, 0).css(opts.split, newPos).css(opts.fixed,  splitter._DF);
            B.css(opts.origin, newPos+bar._DA)
                .css(opts.split, splitter._DA-bar._DA-newPos).css(opts.fixed,  splitter._DF);
            // IE fires resize for us; all others pay cash
            if ( !$.browser.msie )
                panes.trigger("resize");
        }
        function dimSum(jq, dims) {
            // Opera returns -1 for missing min/max width, turn into 0
            var sum = 0;
            for ( var i=1; i < arguments.length; i++ )
                sum += Math.max(parseInt(jq.css(arguments[i])) || 0, 0);
            return sum;
        }
        
        // Determine settings based on incoming opts, element classes, and defaults
        var vh = (args.splitHorizontal? 'h' : args.splitVertical? 'v' : args.type) || 'v';
        var opts = $.extend({
            activeClass: 'active',  // class name for active splitter
            pxPerKey: 8,            // splitter px moved per keypress
            tabIndex: 0,            // tab order indicator
            accessKey: ''           // accessKey for splitbar
        },{
            v: {                    // Vertical splitters:
                keyLeft: 39, keyRight: 37, cursor: "e-resize",
                splitbarClass: "vsplitbar", outlineClass: "voutline",
                type: 'v', eventPos: "pageX", origin: "left",
                split: "width",  pxSplit: "offsetWidth",  side1: "Left", side2: "Right",
                fixed: "height", pxFixed: "offsetHeight", side3: "Top",  side4: "Bottom"
            },
            h: {                    // Horizontal splitters:
                keyTop: 40, keyBottom: 38,  cursor: "n-resize",
                splitbarClass: "hsplitbar", outlineClass: "houtline",
                type: 'h', eventPos: "pageY", origin: "top",
                split: "height", pxSplit: "offsetHeight", side1: "Top",  side2: "Bottom",
                fixed: "width",  pxFixed: "offsetWidth",  side3: "Left", side4: "Right"
            }
        }[vh], args);

        // Create jQuery object closures for splitter and both panes
        var splitter = $(this).css({position: "relative"});
        var panes = $(">*", splitter[0]).css({
            position: "absolute",           // positioned inside splitter container
            "z-index": "1",                 // splitbar is positioned above
            "-moz-outline-style": "none"    // don't show dotted outline
        });
        var A = $(panes[0]);        // left  or top
        var B = $(panes[1]);        // right or bottom

        // Focuser element, provides keyboard support; title is shown by Opera accessKeys
        var focuser = $('<a href="javascript:void(0)"></a>')
            .attr({accessKey: opts.accessKey, tabIndex: opts.tabIndex, title: opts.splitbarClass})
            .bind($.browser.opera?"click":"focus", function(){ this.focus(); bar.addClass(opts.activeClass) })
            .bind("keydown", function(e){
                var key = e.which || e.keyCode;
                var dir = key==opts["key"+opts.side1]? 1 : key==opts["key"+opts.side2]? -1 : 0;
                if ( dir )
                    resplit(A[0][opts.pxSplit]+dir*opts.pxPerKey, false);
            })
            .bind("blur", function(){ bar.removeClass(opts.activeClass) });
            
        // Splitbar element, can be already in the doc or we create one
        var bar = $(panes[2] || '<div></div>')
            .insertAfter(A).css("z-index", "100").append(focuser)
            .attr({"class": opts.splitbarClass, unselectable: "on"})
            .css({position: "absolute", "user-select": "none", "-webkit-user-select": "none",
                "-khtml-user-select": "none", "-moz-user-select": "none"})
            .bind("mousedown", startSplitMouse);
        // Use our cursor unless the style specifies a non-default cursor
        if ( /^(auto|default|)$/.test(bar.css("cursor")) )
            bar.css("cursor", opts.cursor);

        // Cache several dimensions for speed, rather than re-querying constantly
        bar._DA = bar[0][opts.pxSplit];
        splitter._PBF = $.boxModel? dimSum(splitter, "border"+opts.side3+"Width", "border"+opts.side4+"Width") : 0;
        splitter._PBA = $.boxModel? dimSum(splitter, "border"+opts.side1+"Width", "border"+opts.side2+"Width") : 0;
        A._pane = opts.side1;
        B._pane = opts.side2;
        $.each([A,B], function(){
            this._min = opts["min"+this._pane] || dimSum(this, "min-"+opts.split);
            this._max = opts["max"+this._pane] || dimSum(this, "max-"+opts.split) || 9999;
            this._init = opts["size"+this._pane]===true ?
                parseInt($.curCSS(this[0],opts.split)) : opts["size"+this._pane];
        });
        
        // Determine initial position, get from cookie if specified
        var initPos = A._init;
        if ( !isNaN(B._init) )  // recalc initial B size as an offset from the top or left side
            initPos = splitter[0][opts.pxSplit] - splitter._PBA - B._init - bar._DA;
        if ( opts.cookie ) {
            if ( !$.cookie )
                alert('jQuery.splitter(): jQuery cookie plugin required');
            var ckpos = parseInt($.cookie(opts.cookie));
            if ( !isNaN(ckpos) )
                initPos = ckpos;
            $(window).bind("unload", function(){
                var state = String(bar.css(opts.origin));   // current location of splitbar
                $.cookie(opts.cookie, state, {expires: opts.cookieExpires || 365, 
                    path: opts.cookiePath || document.location.pathname});
            });
        }
        if ( isNaN(initPos) )   // King Solomon's algorithm
            initPos = Math.round((splitter[0][opts.pxSplit] - splitter._PBA - bar._DA)/2);

        // Resize event propagation and splitter sizing
        if ( opts.anchorToWindow ) {
            // Account for margin or border on the splitter container and enforce min height
            splitter._hadjust = dimSum(splitter, "borderTopWidth", "borderBottomWidth", "marginBottom");
            splitter._hmin = Math.max(dimSum(splitter, "minHeight"), 20);
            $(window).bind("resize", function(){
                var top = splitter.offset().top;
                var wh = $(window).height();
                splitter.css("height", Math.max(wh-top-splitter._hadjust, splitter._hmin)+"px");
                if ( !$.browser.msie ) splitter.trigger("resize");
            }).trigger("resize");
        }
        else if ( opts.resizeToWidth && !$.browser.msie )
            $(window).bind("resize", function(){
                splitter.trigger("resize"); 
            });

        // Resize event handler; triggered immediately to set initial position
        splitter.bind("resize", function(e, size){
            // Custom events bubble in jQuery 1.3; don't get into a Yo Dawg
            if ( e.target != this ) return;
            // Determine new width/height of splitter container
            splitter._DF = splitter[0][opts.pxFixed] - splitter._PBF;
            splitter._DA = splitter[0][opts.pxSplit] - splitter._PBA;
            // Bail if splitter isn't visible or content isn't there yet
            if ( splitter._DF <= 0 || splitter._DA <= 0 ) return;
            // Re-divvy the adjustable dimension; maintain size of the preferred pane
            resplit(!isNaN(size)? size : (!(opts.sizeRight||opts.sizeBottom)? A[0][opts.pxSplit] :
                splitter._DA-B[0][opts.pxSplit]-bar._DA));
        }).trigger("resize" , [initPos]);
    });
};

});


head.ready(function() {
 
    if ($("#centerandright").length)
    {
   
        // Main vertical splitter, anchored to the browser window
        $("#content").splitter({
            type: "v",
            outline: true,
            minLeft: 100, sizeLeft: 150,
            anchorToWindow: true
        });
        // Second vertical splitter, nested in the right pane of the main one.
   
        $("#centerandright").splitter({
            type: "v",
            outline: true,
            minLeft: 250, sizeLeft: 150
        });
   
   
    /*

        $("#centerandright").splitter({
            type: "h",
            outline: true,
            minTop: 100,
            minBottom: 300,
            anchorToWindow: true,

        });

     */

 }
 
     function getParameterByName(name) {
         var match = RegExp('[?&]' + name + '=([^&]*)')
                         .exec(window.location.search);
         return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
     }
 
    if (getParameterByName("jumpto"))
    {
        jumpto = getParameterByName("jumpto")
        //Ensure we can't jump to random stuff.
        var alphanumberic = /^([a-zA-Z0-9_-]+)$/;
        if(alphanumberic.test( jumpto ))
        {    
            // If the element exists, find it's parent's offset, then it's.
            // Subtract to find the element height.
            // Then, scroll to the top of the element.
            
            right=(document.getElementById('right')); 
            mytop = $("#" + jumpto ).offset().top; 
            // if ( $("#" + jumpto ).parent() )
            // {
            //     parenttop = $("#" + jumpto ).parent().offset().top; 
            // }
            // else
            // {
            //     parenttop = $("#" + jumpto ).offset().top; 
            // }
            // DivHeight = mytop - parenttop;
            right.scrollTop = mytop; // - DivHeight;   
        }
    }
    
        
    $('a.internal').each( function ()
    {            
        $(this).click(function()
            {   
            $("#spinner").height($(this).parent().height());
            $("#spinner").width($(this).parent().width());
            $("#spinner").css("top", $(this).parent().offset().top).css("left", $(this).parent().offset().left).show()
            head.js($(this).attr('link-destination') + "?js=yes&timestamp=" + Math.round(new Date().getTime())  );            
            return false;
            });
        $(this).attr("link-destination",this.href);
    });
    $('#spinner').hide();

    $(".vote").submit(function(event) {
        voteref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 
        
        /* get some values from elements on the page: */
        var $form = $( this ),
            rating = $form.find( 'input[name="rating"]' ).val(),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, { 'rating': $form.find( 'input[name="rating"]' ).val(),
                       '_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(), 
                       'hash' : $form.find( 'input[name="hash"]' ).val() },
          function( data ) {
              voteref.parent().empty().append( data );
          }
        );
    });                
                
    $(".subscription").submit(function(event) {
        ref = $(this);
        /* stop form from submitting normally */
        event.preventDefault(); 

        /* get some values from elements on the page: */
        var $form = $( this ),
            url = $form.attr( 'action' );

        /* Send the data using post and put the results in a div */
        $.post( url, {'_xsrf' : $form.find( 'input[name="_xsrf"]' ).val() },
          function( data ) {
              ref.empty().append("Done.");
              head.js('/?js=yes&singlediv=left' + "&timestamp=" + Math.round(new Date().getTime())  );            
          }
        );

    });

    $(".reply").click(function(event) {
        event.preventDefault();
        var $msg = $(this).attr('message');
        var $href = $(this).attr('href');
        $.get($href + "?getonly=true",function(data) {
          $('#reply_'+$msg).empty().append("<br>" + data);
        });   
        
    });  

    $('a.details').each( function ()
    {            
        $(this).click(function()
            {   
            userdiv = "details_" + $(this).attr('user');
            if ($("#" + userdiv).is(":visible"))
            {
                $("#" + userdiv).hide()
            }
            else
            {
                $("#" + userdiv).show()
            }
            return false;
            });
    });
    
  
});


function MultiSelector( list_target, max ){

    // Where to write the list
    this.list_target = list_target;
    // How many elements?
    this.count = 0;
    // How many elements?
    this.id = 0;
    // Is there a maximum?
    if( max ){
        this.max = max;
    } else {
        this.max = -1;
    };
    
    /**
     * Add a new file input element
     */
    this.addElement = function( element ){

        // Make sure it's a file input element
        if( element.tagName == 'INPUT' && element.type == 'file' ){

            // Element name -- what number am I?
            element.name = 'attached_file' + this.id++;

            // Add reference to this object
            element.multi_selector = this;

            // What to do when a file is selected
            element.onchange = function(){

                // New file input
                var new_element = document.createElement( 'input' );
                new_element.type = 'file';

                // Add new element
                this.parentNode.insertBefore( new_element, this );

                // Apply 'update' to element
                this.multi_selector.addElement( new_element );

                // Update list
                this.multi_selector.addListRow( this );

                // Hide this: we can't use display:none because Safari doesn't like it
                this.style.position = 'absolute';
                this.style.left = '-1000px';

            };
            // If we've reached maximum number, disable input element
            if( this.max != -1 && this.count >= this.max ){
                element.disabled = true;
            };

            // File element counter
            this.count++;
            // Most recent element
            this.current_element = element;
            
        } else {
            // This can only be applied to file input elements!
            alert( 'Error: not a file input element' );
        };

    };

    /**
     * Add a new row to the list of files
     */
    this.addListRow = function( element ){

        // Row div
        var new_row = document.createElement( 'div' );

        // Delete button
        var new_row_button = document.createElement( 'input' );
        new_row_button.type = 'button';
        new_row_button.value = 'Delete';

        // References
        new_row.element = element;

        // Delete function
        new_row_button.onclick= function(){

            // Remove element from form
            this.parentNode.element.parentNode.removeChild( this.parentNode.element );

            // Remove this row from the list
            this.parentNode.parentNode.removeChild( this.parentNode );

            // Decrement counter
            this.parentNode.element.multi_selector.count--;

            // Re-enable input element (if it's disabled)
            this.parentNode.element.multi_selector.current_element.disabled = false;

            // Appease Safari
            //    without it Safari wants to reload the browser window
            //    which nixes your already queued uploads
            return false;
        };

        // Set row value
        new_row.innerHTML = element.value;

        // Add button
        new_row.appendChild( new_row_button );

        // Add it to the list
        this.list_target.appendChild( new_row );
        
    };

};