// This source code is subject to the terms of the Mozilla Public License 2.0 at [https://mozilla.org/MPL/2.0/](https://mozilla.org/MPL/2.0/)
// © adrojatrupen
//@version=6


indicator("Trade Setup T" , overlay = true)


offset = input.int(title = "Global Offset" , defval = 0 , minval = 0 , maxval = 0)


///////////////////Moving Average///////////////////


//***************************100, 190 and 210 Moving Avg***************************//
var ma_fill_color = color.black
if close > ta.sma(close , 200)
    ma_fill_color := color.new(color.green , 60)
if close < ta.sma(close , 200)
    ma_fill_color := color.new(color.red , 60)


var ma100 = plot(ta.sma(close , 50) , color = color.white , title = "MA-100" , offset = offset , style = plot.style_line)
// var ma190 = plot(ta.sma(close , 90) , color = ma_fill_color, title = "MA-190" , offset = offset , style = plot.style_line)
// var ma200 = plot(ta.sma(close , 100) , color = color.white, title = "MA-200" , offset = offset , style = plot.style_line)
// var ma210 = plot(ta.sma(close , 110) , color = ma_fill_color, title = "MA-210" , offset = offset , style = plot.style_line)
// fill(ma190 , ma210 , color = ma_fill_color , title = "Moving Avg BG")
//***************************100, 190 and 210 Moving Avg***************************//


//***************************44 Moving Avg***************************//
var color ma_color = color.black
if ta.sma(close, 4) < ta.sma(close, 20)
    ma_color := color.rgb(255, 55, 55)
if ta.sma(close, 4) > ta.sma(close, 20)
    ma_color := color.rgb(0, 255, 55)
plot(ta.sma(close, 22) , color = ma_color , title = "MA-44" , offset = offset , style = plot.style_line)
//***************************44 Moving Avg***************************//


///////////////////Moving Average///////////////////


///////////////////Super Trand///////////////////


atrPeriod = input(10 , "Super Trand ATR Length")
factor = input.float(3.0 , "Super Trand Factor" , step = 0.01)


[supertrend , direction] = ta.supertrend(factor , atrPeriod)


bodyMiddle = plot((open + close) / 2 , display = display.none , title = "Super Trand MiddelBody")
upTrend = plot(direction < 0 ? supertrend : na , "Super Trand Up" , color = color.green , style=plot.style_linebr)
downTrend = plot(direction < 0? na : supertrend , "Super Trand Down" , color = color.red , style=plot.style_linebr)


// fill(bodyMiddle , upTrend , color.new(color.green , 90) , fillgaps=false , title = "Super Trand Up")
// fill(bodyMiddle , downTrend , color.new(color.red, 90) , fillgaps=false , title = "Super Trand Down")


///////////////////Super Trand///////////////////


///////////////////Buy Sell Call///////////////////
src = close


keyvalue = input.int(3 , title = 'Buy Sell Sensitivity')
// keyvalue -- min = 3 -- max = 6    best -- 5
atrperiod = input(20 , title = 'Buy Sell ATR Period')
xATR = ta.atr(atrperiod)
nLoss = keyvalue * xATR


xATRTrailingStop = 0.0
iff_1 = src > nz(xATRTrailingStop[1], 0) ? src - nLoss : src + nLoss
iff_2 = src < nz(xATRTrailingStop[1], 0) and src[1] < nz(xATRTrailingStop[1], 0) ? math.min(nz(xATRTrailingStop[1]), src + nLoss) : iff_1
xATRTrailingStop := src > nz(xATRTrailingStop[1], 0) and src[1] > nz(xATRTrailingStop[1], 0) ? math.max(nz(xATRTrailingStop[1]), src - nLoss) : iff_2


pos = 0
iff_3 = src[1] > nz(xATRTrailingStop[1], 0) and src < nz(xATRTrailingStop[1], 0) ? -1 : nz(pos[1], 0)
pos := src[1] < nz(xATRTrailingStop[1], 0) and src > nz(xATRTrailingStop[1], 0) ? 1 : iff_3


xcolor = pos == -1 ? color.red : pos == 1 ? color.green : color.blue


plot(xATRTrailingStop, color=xcolor, title='Buy Sell Trailing Stop Loss', style=plot.style_circles)
buy = ta.crossover(src, xATRTrailingStop)
sell = ta.crossunder(src, xATRTrailingStop)
barcolor = src > xATRTrailingStop



// Modified plotshape - only show signals when market is trending (not sideways)
plotshape(buy, title = 'Buy', text = 'Buy', style = shape.labelup, location = location.belowbar, color = color.new(color.green, 0), textcolor = color.new(color.white, 0), size = size.tiny)
plotshape(sell, title = 'Sell', text = 'Sell', style = shape.labeldown, color = color.new(color.red, 0), textcolor = color.new(color.white, 0), size = size.tiny)


if buy
    alert(message = 'Buy' , freq = alert.freq_once_per_bar_close)


if sell
    alert(message = 'Sell', freq = alert.freq_once_per_bar_close)


///////////////////Buy Sell Call///////////////////


// Bollinger Bands settings - 1
basis_length = input.int(20, minval=1, title="Bollinger Bands Basis Length")
mult = input.float(2.0, minval=0.001, maxval=50, title="Standard Deviation Multiplier")


// Calculate Bollinger Bands without the baseline
basis = ta.sma(close, basis_length)
dev = mult * ta.stdev(close, basis_length)
upper = basis + dev
lower = basis - dev


// Plot the upper and lower bands of Bollinger Bands
// p1 = plot(upper, "Upper Band", color=color.red, linewidth=1)
// p2 = plot(lower, "Lower Band", color=color.green, linewidth=1)