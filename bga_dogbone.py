from pcbnew import *
from bga_utils import *
from math import sqrt
import wx

# 20170902 - Greg Smith
#     Added pbyn to replace Pad.GetNetCode()
#     Added ActionPlugin support
#     Added dialog to request skip layers and layer quadrants

def make_dogbone(board, mod, bga_info, skip_outer, edge_layers):
    vias = []

    #GetNodesCount:
    pbyn={};k=[pbyn.setdefault(p.GetNetCode(),[]).append(p) for p in GetBoard().GetPads()]

    for first_pad in mod.Pads():
        if len(pbyn[first_pad.GetNetCode()]) > 1:
            break

    netclasses = board.GetDesignSettings().GetNetClasses()
    nc = netclasses.GetDefault()
    #net = first_pad.GetNet()
    #nc = net.GetNetClass()
    via_dia = nc.GetViaDiameter()
    via_drill = nc.GetViaDrill()
    isolation = nc.GetClearance()
    track_width = nc.GetTrackWidth()
    dist = bga_info.spacing

    fy = sqrt((isolation+via_dia)**2-(dist/2)**2)
    fx = sqrt((isolation+via_dia)**2-fy**2)

    ofsx = fx/2
    ofsy = (dist-fy)/2

    #for pad in mod.Pads():
    for pad in list(filter(lambda p: p.GetNetCode()>0,mod.Pads())):
    #for pad in list(filter(lambda p: p.GetNet().GetNodesCount() > 1, mod.Pads())):
        pad_pos = get_pad_position(bga_info, pad)
        if is_pad_outer_ring(bga_info, pad_pos, skip_outer):
            continue
        if is_edge_layer(bga_info,pad_pos,edge_layers):
            horizontal = abs(pad.GetPosition().x - bga_info.center.x) > abs(pad.GetPosition().y - bga_info.center.y)

            if horizontal:
                if (pad_pos.y-edge_layers) % 2 == 0:
                    ep = pad.GetPosition() + wxPoint(ofsx, -ofsy)
                else:
                    ep = pad.GetPosition() + wxPoint(-ofsx, ofsy)
            else:
                if (pad_pos.x-edge_layers) % 2 == 0:
                    ep = pad.GetPosition() + wxPoint(ofsy, -ofsx)
                else:
                    ep = pad.GetPosition() + wxPoint(-ofsy, ofsx)
        elif (edge_layers>0) and is_edge_layer(bga_info,pad_pos,edge_layers+1):
            horizontal = abs(pad.GetPosition().x - bga_info.center.x) > abs(pad.GetPosition().y - bga_info.center.y)

            dx = 1 if (pad.GetPosition().x - bga_info.center.x) > 0 else -1
            dy = 1 if (pad.GetPosition().y - bga_info.center.y) > 0 else -1

            if horizontal:
                ep = pad.GetPosition() + wxPoint(dx * ofsx, -dx * ofsy)
            else:
                ep = pad.GetPosition() + wxPoint(-dy * ofsy, dy * ofsx)
        else:
            dx = 1 if (pad.GetPosition().x - bga_info.center.x) > 0 else -1
            dy = 1 if (pad.GetPosition().y - bga_info.center.y) > 0 else -1
            ep = pad.GetPosition() + wxPoint(dx * bga_info.spacing / 2, dy * bga_info.spacing / 2)

        # Create track
        new_track = TRACK(board)
        new_track.SetStart(pad.GetPosition())
        new_track.SetEnd(ep)
        new_track.SetNetCode(pad.GetNetCode())
        new_track.SetLayer(pad.GetLayer())
        new_track.SetWidth(track_width)
        board.Add(new_track)
        # Create via
        new_via = VIA(board)
        new_via.SetPosition(ep)
        new_via.SetNetCode(pad.GetNetCode())
        new_via.SetDrill(via_drill)
        new_via.SetWidth(via_dia)
        board.Add(new_via)
        vias.append(new_via)
    return vias


def make_dogbones(board, mod, skip_outer, edge_layers):
    info = get_bga_info(mod)
    return [info.spacing, make_dogbone(board, mod, info, skip_outer, edge_layers)]

def run_original():
    my_board = LoadBoard("test11.kicad_pcb")
    my_board.BuildListOfNets()

    mod = my_board.FindModuleByReference("t.xc7.inst")

    # Skip zero layers and route 6 layer quadrants with shifted vias and 1 transition layer
    data = make_dogbones(my_board, mod, 0, 6)

    SaveBoard("test1.kicad_pcb", my_board)

def help():
    print("This python script runs on the currently-loaded board and the selected module.")

def run():
    my_board = GetBoard()
    my_board.BuildListOfNets()

    #mod = my_board.FindModuleByReference("t.xc7.inst")
    mod = list(filter(lambda m: m.IsSelected(), my_board.GetFootprints()))

    if len(mod) != 1:
        wx.MessageDialog(None,message="This python script runs on the currently-loaded board and the selected module.",style=wx.OK).ShowModal()
        return

    d = wx.TextEntryDialog(None,message="Enter Number of Layers to Skip")
    if d.ShowModal() != wx.ID_OK:
        return

    try: skip = int(d.GetValue())
    except: return

    d = wx.TextEntryDialog(None,message="Enter Number of Layer Quadrants")
    if d.ShowModal() != wx.ID_OK:
        return

    try: quadrants = int(d.GetValue())
    except: return

    # Skip zero layers and route 6 layer quadrants with shifted vias and 1 transition layer
    data = make_dogbones(my_board, mod[0], skip, quadrants)

class menu(ActionPlugin):
    def defaults( self ):
        """Support for ActionPlugin"""
        self.name = "BGA Dogbone"
        self.category = "Layout"
        self.description = "Create dogbones on the selected BGA."
    def Run(self):
        run()

try:
    menu().register()
except:
    pass
