// SPDX-License-Identifier: Apache-2.0
using System;
using System.Linq;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
namespace Ivad.Annotator {
 // Selection model is independent of WPF SelectedItems. Only realized rows are painted.
 public sealed class RangeFrameList:ListBox {
  public readonly HashSet<string> Ids=new HashSet<string>();
  int anchor=-1,extent=-1;bool internalSelection,rangeSelection;
  public event Action RangeChanged;
  public static readonly DependencyProperty BatchSelectedProperty=DependencyProperty.RegisterAttached("BatchSelected",typeof(bool),typeof(RangeFrameList),new PropertyMetadata(false));
  public static bool GetBatchSelected(DependencyObject o){return (bool)o.GetValue(BatchSelectedProperty);}
  public static void SetBatchSelected(DependencyObject o,bool v){o.SetValue(BatchSelectedProperty,v);}
  public RangeFrameList(){SelectionMode=SelectionMode.Extended;ScrollViewer.SetCanContentScroll(this,true);VirtualizingStackPanel.SetIsVirtualizing(this,true);VirtualizingStackPanel.SetVirtualizationMode(this,VirtualizationMode.Recycling);AddHandler(ScrollViewer.ScrollChangedEvent,new ScrollChangedEventHandler((s,e)=>Paint()));}
  protected override void OnItemsChanged(System.Collections.Specialized.NotifyCollectionChangedEventArgs e){base.OnItemsChanged(e);Ids.Clear();anchor=extent=-1;rangeSelection=false;Notify();}
  protected override void OnSelectionChanged(SelectionChangedEventArgs e){if(!internalSelection){if(rangeSelection||(e.RemovedItems.Count>0&&e.AddedItems.Count>0))Ids.Clear();rangeSelection=false;foreach(Choice c in e.RemovedItems)Ids.Remove(c.Id);foreach(Choice c in e.AddedItems)Ids.Add(c.Id);anchor=extent=SelectedIndex;}base.OnSelectionChanged(e);Notify();}
  public void SelectRange(int first,int last,bool additive){
   if(first<0||last<0||first>=Items.Count||last>=Items.Count)return;
   int lo=Math.Min(first,last),hi=Math.Max(first,last);
   if(!additive&&rangeSelection&&anchor==first&&extent>=0){int oldLo=Math.Min(anchor,extent),oldHi=Math.Max(anchor,extent);for(int i=oldLo;i<lo;i++)Ids.Remove(((Choice)Items[i]).Id);for(int i=hi+1;i<=oldHi;i++)Ids.Remove(((Choice)Items[i]).Id);for(int i=lo;i<oldLo;i++)Ids.Add(((Choice)Items[i]).Id);for(int i=oldHi+1;i<=hi;i++)Ids.Add(((Choice)Items[i]).Id);}
   else{if(!additive)Ids.Clear();for(int i=lo;i<=hi;i++)Ids.Add(((Choice)Items[i]).Id);}rangeSelection=!additive;
   anchor=first;extent=last;Notify();
  }
  public string[] SelectionIds(){return Ids.ToArray();}
  public void ResetSelection(){Ids.Clear();anchor=extent=-1;rangeSelection=false;Notify();}
  void Notify(){Paint();if(RangeChanged!=null)RangeChanged();}
  void Paint(){PaintTree(this);}
  protected override void PrepareContainerForItemOverride(DependencyObject element,object item){base.PrepareContainerForItemOverride(element,item);var c=item as Choice;SetBatchSelected(element,c!=null&&Ids.Contains(c.Id));}
  void PaintTree(DependencyObject node){for(int i=0;i<VisualTreeHelper.GetChildrenCount(node);i++){var child=VisualTreeHelper.GetChild(node,i);var row=child as ListBoxItem;if(row!=null){var c=row.DataContext as Choice;SetBatchSelected(row,c!=null&&Ids.Contains(c.Id));}else PaintTree(child);}}
  int Hit(object source){var row=ItemsControl.ContainerFromElement(this,source as DependencyObject) as ListBoxItem;return row==null?-1:ItemContainerGenerator.IndexFromContainer(row);}
  protected override void OnPreviewMouseLeftButtonDown(MouseButtonEventArgs e){int i=Hit(e.OriginalSource);if(i<0){base.OnPreviewMouseLeftButtonDown(e);return;}Focus();bool shift=(Keyboard.Modifiers&ModifierKeys.Shift)!=0,ctrl=(Keyboard.Modifiers&ModifierKeys.Control)!=0;
   if(shift){SelectRange(anchor<0?i:anchor,i,ctrl);}else if(ctrl){rangeSelection=false;string id=((Choice)Items[i]).Id;if(!Ids.Remove(id))Ids.Add(id);anchor=extent=i;Notify();}else{rangeSelection=false;internalSelection=true;try{SelectedIndex=i;}finally{internalSelection=false;}Ids.Clear();Ids.Add(((Choice)Items[i]).Id);anchor=extent=i;Notify();}e.Handled=true;
  }
  protected override void OnPreviewMouseMove(MouseEventArgs e){if(e.LeftButton==MouseButtonState.Pressed&&(Keyboard.Modifiers&ModifierKeys.Shift)!=0){int i=Hit(e.OriginalSource);if(i>=0&&i!=extent)SelectRange(anchor<0?i:anchor,i,(Keyboard.Modifiers&ModifierKeys.Control)!=0);e.Handled=true;}base.OnPreviewMouseMove(e);}
  protected override void OnPreviewKeyDown(KeyEventArgs e){bool shift=(Keyboard.Modifiers&ModifierKeys.Shift)!=0,ctrl=(Keyboard.Modifiers&ModifierKeys.Control)!=0;
   if(ctrl&&e.Key==Key.A){SelectRange(0,Items.Count-1,false);e.Handled=true;return;}
   if(shift&&Items.Count>0&&new[]{Key.Up,Key.Down,Key.Home,Key.End,Key.PageUp,Key.PageDown}.Contains(e.Key)){int step=e.Key==Key.Down?1:e.Key==Key.Up?-1:e.Key==Key.PageUp?-10:10;int i=e.Key==Key.Home?0:e.Key==Key.End?Items.Count-1:Math.Max(0,Math.Min(Items.Count-1,(extent<0?SelectedIndex:extent)+step));SelectRange(anchor<0?i:anchor,i,ctrl);ScrollIntoView(Items[i]);e.Handled=true;return;}
   if(ctrl&&e.Key==Key.Space&&SelectedItem!=null){rangeSelection=false;string id=((Choice)SelectedItem).Id;if(!Ids.Remove(id))Ids.Add(id);Notify();e.Handled=true;return;}base.OnPreviewKeyDown(e);
  }
 }
}
