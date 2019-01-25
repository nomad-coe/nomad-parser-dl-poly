/*
 * Copyright 2016-2018 Carl Poelking, Fawzi Mohamed, Ankit Kariryaa
 * 
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 * 
 *     http://www.apache.org/licenses/LICENSE-2.0
 * 
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */

package eu.nomad_lab.parsers

import eu.{ nomad_lab => lab }
import eu.nomad_lab.DefaultPythonInterpreter
import org.{ json4s => jn }
import scala.collection.breakOut

object DlPolyParser extends SimpleExternalParserGenerator(
  name = "DlPolyParser",
  parserInfo = jn.JObject(
    ("name" -> jn.JString("DlPolyParser")) ::
      ("parserId" -> jn.JString("DlPolyParser" + lab.DlPolyVersionInfo.version)) ::
      ("versionInfo" -> jn.JObject(
        ("nomadCoreVersion" -> jn.JObject(lab.NomadCoreVersionInfo.toMap.map {
          case (k, v) => k -> jn.JString(v.toString)
        }(breakOut): List[(String, jn.JString)])) ::
          (lab.DlPolyVersionInfo.toMap.map {
            case (key, value) =>
              (key -> jn.JString(value.toString))
          }(breakOut): List[(String, jn.JString)])
      )) :: Nil
  ),
  mainFileTypes = Seq("text/.*"),
  mainFileRe = """ DL_POLY """.r,
  cmd = Seq(DefaultPythonInterpreter.pythonExe(), "${envDir}/parsers/dl-poly/parser/parser-dl_poly/dlPolyParser.py",
    "${mainFilePath}"),
  resList = Seq(
    "parser-dl_poly/dlPolyParser.py",
    "parser-dl_poly/libDlPolyParser.py",
    "parser-dl_poly/libMomo.py",
    "parser-dl_poly/setup_paths.py",
    "nomad_meta_info/public.nomadmetainfo.json",
    "nomad_meta_info/common.nomadmetainfo.json",
    "nomad_meta_info/meta.nomadmetainfo.json",
    "nomad_meta_info/dl_poly.nomadmetainfo.json"
  ) ++ DefaultPythonInterpreter.commonFiles(),
  dirMap = Map(
    "parser-dl_poly" -> "parsers/dl-poly/parser/parser-dl_poly",
    "nomad_meta_info" -> "nomad-meta-info/meta_info/nomad_meta_info"
  ) ++ DefaultPythonInterpreter.commonDirMapping()
)
