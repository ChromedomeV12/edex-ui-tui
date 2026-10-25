--- @sync entry
-- GPL-3.0; UI uses Yazi 26.9.1's public Current/Tab/Entity component APIs.
local M = {}
local ink, muted, selection = "#aacfd1", "#586c6f", "#161c21"
local state = { cols = 1, rows = 1 }
local ids, marks = {}, {}
for name, id in (os.getenv("EDEX_ICON_IDS") or ""):gmatch("([%w_]+)=(%d+)") do
  ids[name] = tonumber(id)
end
for _, cp in utf8.codes(os.getenv("EDEX_ICON_MARKS") or "") do marks[#marks + 1] = utf8.char(cp) end

local function icon(name, area)
  local id = ids[name] or ids.file
  if not id or #marks < 6 then
    return ui.Text(name == "folder" and "▗▄▄▄▄\n▐████▌" or "▗██▄\n▐███▌"):area(area):fg(ink):align(ui.Align.CENTER)
  end
  local rows = {}
  for row = 0, 2 do
    local cells = ""
    for col = 0, 5 do cells = cells .. utf8.char(0x10eeee) .. marks[row + 1] .. marks[col + 1] end
    rows[#rows + 1] = ui.Line(cells):fg(string.format("#%06x", id))
  end
  return ui.Text(rows):area(area)
end

local function file_icon(file)
  if file.cha.is_link then return "symlink" end
  if file.cha.is_dir then return "folder" end
  local ext = tostring(file.name):match("%.([^%.]+)$") or ""
  local types = { py="python",js="javascript",mjs="javascript",json="json",md="markdown",sh="shell",bash="shell",css="css",html="html",toml="config",conf="config",png="image",jpg="image",svg="image" }
  return types[ext:lower()] or "file"
end

-- Pure grid geometry shared by drawing, key movement, mouse hits and tests.
local model = {}
function model.layout(w, h, cursor, count)
  local cols=math.max(1, math.floor(w/13))
  local pitch=h>=4 and 5 or 1
  local rows=math.max(1, math.floor(h/pitch))
  local size=cols*rows
  local shortcuts=size>=3 and 2 or 0
  local start=math.floor((math.max(0,cursor)+shortcuts)/size)*size
  return {cols=cols,rows=rows,size=size,shortcuts=shortcuts,start=start,pitch=pitch,
          width=math.max(1,math.floor(w/cols)),count=count}
end
function model.target(cursor,count,cols,rows,direction)
  if count==0 then return nil end
  local steps={left=-1,right=1,prev=-1,next=1,up=-cols,down=cols,
               pageup=-cols*rows,pagedown=cols*rows,first=-count,last=count}
  local step=steps[direction]
  if not step then return nil end
  return math.max(0,math.min(count-1,cursor+step))
end
function model.hit(g,x,y,w,h)
  if x<0 or y<0 or x>=w or y>=h then return nil end
  local col=math.floor(x/g.width);local row=math.floor(y/g.pitch)
  if col>=g.cols or row>=g.rows then return nil end
  local index=g.start+row*g.cols+col
  if index>=g.count+g.shortcuts then return nil end
  return index
end
M.model=model
local function activate(file)
  if not file then return end
  if file.cha.is_dir then ya.emit("enter",{}) else ya.emit("open",{hovered=true}) end
end

function M:setup()
  -- Removing the stock list rails avoids a misleading vertical-list cursor.
  function Tab:build()
    self._children = { Current:new(self._area:pad(ui.Pad.x(1)), self._tab) }
  end
  function Current:grid()
    local g=model.layout(self._area.w,self._area.h,self._folder.cursor,#self._folder.files)
    state.cols=g.cols;state.rows=g.rows;state.shortcuts=g.shortcuts
    return g
  end
  function Current:redraw()
    local files=self._folder.files
    local g=self:grid();local output={}
    for n=0,g.size-1 do
      local index=g.start+n
      local file=index>=g.shortcuts and files[index-g.shortcuts+1] or nil
      if index>=g.shortcuts and not file then break end
      local x=self._area.x+(n%g.cols)*g.width
      local y=self._area.y+math.floor(n/g.cols)*g.pitch
      local hovered=file and file.is_hovered
      local selected=file and file:is_selected()
      local caption=index==0 and g.shortcuts>0 and "Root /" or index==1 and g.shortcuts>0 and "Go up" or file.name
      if selected then caption="* "..caption end
      caption=ui.truncate(ui.printable(caption),{max=math.max(1,g.width-2)})
      local label=ui.Line(caption):fg(hovered and ink or muted):align(ui.Align.CENTER)
      if hovered then label=label:bg(selection):bold() elseif selected then label=label:bold() end
      local name=index==0 and g.shortcuts>0 and "disk" or index==1 and g.shortcuts>0 and "up" or file_icon(file)
      if g.pitch>=4 and g.width>=6 then
        output[#output+1]=icon(name,ui.Rect{x=x+math.max(0,math.floor((g.width-6)/2)),y=y,w=6,h=3})
      end
      output[#output+1]=label:area(ui.Rect{x=x,y=y+(g.pitch>=4 and 3 or 0),w=g.width,h=1})
    end
    if #files==0 and self._area.h>g.pitch then
      local message=files.filter and "No filter results" or "Empty directory"
      local done,err=self._folder.stage()
      if not done then message="Loading..." elseif err then message="Error: "..tostring(err) end
      output[#output+1]=ui.Text(message):fg(muted):align(ui.Align.CENTER):area(ui.Rect{x=self._area.x,y=self._area.y+g.pitch,w=self._area.w,h=1})
    end
    return output
  end
  function Current:click(event,up)
    if up or event.is_middle then return end
    local g=self:grid()
    local index=model.hit(g,event.x-self._area.x,event.y-self._area.y,self._area.w,self._area.h)
    if not index then return end
    if g.shortcuts>0 and index==0 then ya.emit("cd",{"/"});return end
    if g.shortcuts>0 and index==1 then ya.emit("leave",{});return end
    local file=self._folder.files[index-g.shortcuts+1]
    if not file then return end
    ya.emit("reveal",{file.url})

  end
  function Current:scroll(event,step)
    local g=self:grid();local count=#self._folder.files
    if count>0 then
      local target=math.max(0,math.min(count-1,self._folder.cursor+step*g.cols))
      ya.emit("arrow",{target-self._folder.cursor})
    end
  end
  function Header:redraw()
    local width=self._area.w
    local path=ui.truncate(ya.readable_path(tostring(self._current.cwd)),{max=math.max(0,width-14),rtl=true})
    return {ui.Line("FILESYSTEM"):fg(ink):area(self._area),ui.Line(path):fg(muted):align(ui.Align.RIGHT):area(self._area)}
  end
  function Status:redraw()
    local current=self._current
    local file=current.hovered
    local name=file and ui.printable(file.name) or ""
    local mode=tostring(self._tab.mode):upper()
    local page=math.floor((current.cursor+(state.shortcuts or 2))/(state.cols*state.rows))+1
    local pages=math.max(1,math.ceil((#current.files+(state.shortcuts or 2))/(state.cols*state.rows)))
    local left=mode.." | "..#current.files.." items | Page "..page.."/"..pages.." | "..name
    left=ui.truncate(left,{max=math.max(0,self._area.w-12)})
    local position=(#current.files>0 and (current.cursor+1) or 0).." / "..#current.files
    return {ui.Line(left):fg(muted):area(self._area),ui.Line(position):fg(ink):align(ui.Align.RIGHT):area(self._area)}
  end
end

function M:entry(job)
  local direction=job.args[1]
  local current=cx.active.current
  if direction=="activate" then activate(current.hovered);return end
  local target=model.target(current.cursor,#current.files,state.cols,state.rows,direction)
  if target then ya.emit("arrow",{target-current.cursor}) end
end
return M
