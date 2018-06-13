import { reduce } from 'lodash'
import template from './todo-list.html'
// import moment from 'moment-timezone'
import './todo-list.scss'

export default function todoList (orchestraApi) {
  'ngAnnotate'
  return {
    template,
    restrict: 'E',
    scope: {
      projectId: '=',
      taskId: '='
    },
    controllerAs: 'todoList',
    bindToController: true,
    controller: function (todoApi, $scope) {
      var todoList = this
      todoList.possibleTasks = []
      todoList.newTodoTaskId = null
      todoList.newTodoDescription = null
      todoList.newTodoStartDate = null
      todoList.newTodoDueDate = null
      todoList.ready = false
      todoList.taskSlugs = {}
      todoList.todos = []

      todoList.canAddTodo = () => {
        return todoList.newTodoTaskId && todoList.newTodoDescription
      }

      todoList.updateTodo = (todo) => {
        console.log(todo)
        // todoApi.update(todo)
      }

      todoList.toggleSkipTodo = (todo) => {
        todo.skipped = !todo.skipped
        // todoApi.update(todo)
      }

      orchestraApi.projectInformation(todoList.projectId)
        .then((response) => {
          const humanSteps = new Set(response.data.steps.filter(step => step.is_human).map(step => step.slug))
          todoList.steps = reduce(
            Object.values(response.data.steps), (result, step) => {
              result[step.slug] = step
              return result
            }, {})
          todoList.taskSlugs = reduce(
            Object.values(response.data.tasks), (result, task) => {
              result[task.id] = task.step_slug
              return result
            }, {})
          todoList.possibleTasks = Object.values(response.data.tasks).filter(task => task.status !== 'Complete' && humanSteps.has(task.step_slug))
          todoList.possibleRoles = ['CSM', 'Designer']

          // TODO(marcua): parallelize requests rather than chaining `then`s.
          todoApi.list(todoList.projectId).then((todos) => {
            todoList.todos = todos
            todoList.ready = true
            console.log(todoList)
          })
        })
    }
  }
}
